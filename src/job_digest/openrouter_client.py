"""OpenRouter API client wrapper."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

import requests
from requests.exceptions import HTTPError, RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import SummaryConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobClassificationResult:
    """Result returned by the job email classifier."""

    relevant_indices: list[int]
    summary: str


@dataclass(frozen=True)
class SummaryResult:
    """Summarisation payload combining plain-text and HTML output."""

    plain_text: str
    html: str


class OpenRouterClient:
    """Client for interacting with OpenRouter chat completions API."""

    def __init__(self, config: SummaryConfig) -> None:
        if not config.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self._config = config

    def _chat_completion(self, chat_messages: list[dict]) -> str:
        payload = {
            "model": self._config.model,
            "messages": chat_messages,
        }

        headers = {
            "Authorization": f"Bearer {self._config.openrouter_api_key}",
            "HTTP-Referer": "https://openrouter.ai/",
            "X-Title": "Job Email Digest",
            "User-Agent": self._config.user_agent,
        }

        try:
            response = requests.post(
                self._config.openrouter_api_url,
                json=payload,
                headers=headers,
                timeout=45,
            )
            response.raise_for_status()
        except HTTPError as exc:
            try:
                error_detail = exc.response.text  # type: ignore[assignment]
            except Exception:  # pragma: no cover - defensive
                error_detail = "<no response body>"
            logger.error(
                "OpenRouter API responded with error %s: %s", exc.response.status_code, error_detail
            )
            raise
        except RequestException as exc:
            logger.exception("OpenRouter API request failed: %s", exc)
            raise

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected OpenRouter response structure: %s", data)
            raise ValueError("Invalid OpenRouter response") from exc

    def _build_summary_payload(self, snippets: Sequence[str]) -> dict:
        return {
            "instructions": [
                "Create a concise daily digest of the supplied emails.",
                "Highlight interviews, offers, deadlines, and explicit action items.",
                "Group similar notifications together where useful.",
                "If nothing important is present, say so plainly.",
            ],
            "emails": [
                {"index": index + 1, "content": snippet}
                for index, snippet in enumerate(snippets)
            ],
        }

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def summarize_messages(
        self, *, snippets: Iterable[str], tone: str, format_hint: str
    ) -> SummaryResult:
        """Generate a summary using OpenRouter."""

        snippet_list = list(snippets)
        payload = {
            "preferred_format": format_hint,
            "tone": tone,
            "digest": self._build_summary_payload(snippet_list),
        }
        chat_messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant that writes daily job email digests with a {tone} tone. "
                    "Respond ONLY with JSON containing keys plain_text_summary and html_summary. "
                    "plain_text_summary must be clear for plain-text emails. "
                    "html_summary must be production-ready HTML using headings and bullet lists."
                ).format(tone=tone),
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ]
        raw_response = self._chat_completion(chat_messages)
        data = self._parse_summary_response(raw_response)
        plain_text = data.get("plain_text_summary") or data.get("text_summary")
        html = data.get("html_summary") or ""
        if not plain_text:
            plain_text = "No job-related emails found in the selected timeframe."
        return SummaryResult(plain_text=plain_text.strip(), html=html.strip())

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def identify_job_emails(self, *, email_contexts: Sequence[dict]) -> JobClassificationResult:
        """Identify which recent emails are job-related using the LLM."""

        if not email_contexts:
            return JobClassificationResult([], "No emails to analyse.")

        system_prompt = (
            "You are an assistant that ONLY responds with JSON. "
            "Determine which emails relate to job opportunities, recruiting, interviews, "
            "offers, or hiring updates. Return an object with keys: "
            "job_related_indices (array of integers referencing the email index field), "
            "summary (string describing notable job-related items)."
        )

        payload_text = json.dumps({"emails": email_contexts}, ensure_ascii=False)
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload_text},
        ]

        raw_response = self._chat_completion(chat_messages)
        data = self._parse_json_response(raw_response, total=len(email_contexts))

        relevant_indices = data.get("job_related_indices") or data.get(
            "job_related_emails", []
        )
        validated_indices = self._normalise_indices(relevant_indices, len(email_contexts))
        summary = data.get("summary") or "No job-related emails found in the selected timeframe."
        return JobClassificationResult(validated_indices, summary.strip())

    def _parse_json_response(self, content: str, total: int) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from OpenRouter response: %s", content)
            logger.error("Invalid JSON response from classifier: %s", content)
            # Fallback: treat all emails as potentially relevant so nothing is missed.
            return {
                "job_related_indices": list(range(1, total + 1)),
                "summary": "Potential job-related content detected; unable to parse classifier response.",
            }

    @staticmethod
    def _normalise_indices(indices: Iterable, total: int) -> list[int]:
        normalised: list[int] = []
        for value in indices or []:
            idx: int | None = None
            if isinstance(value, (int, float)):
                idx = int(value)
            elif isinstance(value, str) and value.strip().isdigit():
                idx = int(value.strip())
            if idx is not None and 1 <= idx <= total:
                normalised.append(idx)
        return sorted(set(normalised))

    def _parse_summary_response(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON summary response: %s", content)
            logger.error("Invalid JSON summary response: %s", content)
            return {
                "plain_text_summary": content.strip(),
                "html_summary": "",
            }

