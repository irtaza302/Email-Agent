"""OpenRouter API client wrapper."""

from __future__ import annotations

import logging
from typing import Iterable

import requests
from requests.exceptions import HTTPError, RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import SummaryConfig

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for interacting with OpenRouter chat completions API."""

    def __init__(self, config: SummaryConfig) -> None:
        if not config.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self._config = config

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def summarize_messages(self, *, snippets: Iterable[str]) -> str:
        """Generate a summary using OpenRouter."""

        prompt = self._build_prompt(snippets)
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": "You are an assistant that writes concise job email digests."},
                {"role": "user", "content": prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._config.openrouter_api_key}",
            "HTTP-Referer": "https://openrouter.ai/",  # required per OpenRouter policy
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
            logger.exception("OpenRouter API responded with error: %s", exc)
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

    def _build_prompt(self, snippets: Iterable[str]) -> str:
        joined = "\n\n".join(snippets)
        return (
            "Summarize the following job-related emails into bullet points. "
            "Highlight interviews, offers, deadlines, and action items. "
            "If nothing important is found, state that clearly.\n\n"
            f"Emails:\n{joined}"
        )

