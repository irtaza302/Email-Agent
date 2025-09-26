"""Logic to convert Gmail messages into summaries."""

from __future__ import annotations

import logging

from .gmail_client import GmailClient
from .openrouter_client import JobClassificationResult, OpenRouterClient

logger = logging.getLogger(__name__)


class JobEmailSummarizer:
    """Coordinate fetching emails and producing a summary."""

    def __init__(
        self,
        *,
        gmail_client: GmailClient,
        openrouter_client: OpenRouterClient,
        max_emails: int,
        timeframe_hours: int,
    ) -> None:
        self._gmail_client = gmail_client
        self._openrouter_client = openrouter_client
        self._max_emails = max_emails
        self._timeframe_hours = timeframe_hours
        self._summary_tone = openrouter_client._config.summarizer_tone  # noqa: SLF001
        self._summary_format = openrouter_client._config.summarizer_format  # noqa: SLF001

    def generate_summary(self) -> tuple[str, list[dict], str, str]:
        """Fetch job messages and generate a summary text."""

        messages = self._gmail_client.fetch_recent_messages(
            timeframe_hours=self._timeframe_hours,
            max_results=self._max_emails,
        )
        if not messages:
            logger.info("No recent emails found in timeframe")
            summary = "No job-related emails found in the selected timeframe."
            return (summary, [], summary, "")

        enriched_messages = []
        classifier_input = []
        for index, message in enumerate(messages, start=1):
            text = self._gmail_client.extract_message_text(message)
            headers = self._gmail_client.extract_headers(
                message, ["Subject", "From", "Date"]
            )
            enriched = {
                "index": index,
                "subject": headers.get("subject", "(No subject)"),
                "sender": headers.get("from", "(Unknown sender)"),
                "date": headers.get("date", ""),
                "body": text,
            }
            enriched_messages.append(enriched)
            classifier_input.append(
                {
                    "index": index,
                    "subject": enriched["subject"],
                    "sender": enriched["sender"],
                    "body_preview": text[:800],
                }
            )

        classification: JobClassificationResult = self._openrouter_client.identify_job_emails(
            email_contexts=classifier_input
        )

        if not classification.relevant_indices:
            logger.info("Classifier found no job-related emails")
            return (classification.summary, [], classification.summary, "")

        relevant_messages = [
            enriched_messages[idx - 1]
            for idx in classification.relevant_indices
            if 1 <= idx <= len(enriched_messages)
        ]

        snippets = [
            self._format_snippet(
                subject=msg["subject"],
                sender=msg["sender"],
                received=msg["date"],
                body=msg["body"],
            )
            for msg in relevant_messages
        ]

        if not snippets:
            logger.info("No relevant snippets after classifier filtering")
            return (classification.summary, [], classification.summary, "")

        summary_result = self._openrouter_client.summarize_messages(
            snippets=snippets,
            tone=self._summary_tone,
            format_hint=self._summary_format,
        )
        return (
            summary_result.plain_text,
            relevant_messages,
            summary_result.plain_text,
            summary_result.html,
        )

    def _format_snippet(
        self, *, subject: str, sender: str, received: str | None, body: str
    ) -> str:
        lines = [
            "- Subject: {subject}",
            "  From: {sender}",
            "  Date: {date}",
        ]
        if body:
            preview_lines = body.strip().splitlines()
            if preview_lines:
                lines.append("  Preview: {preview}")
        else:
            preview_lines = []
        return "\n".join(lines).format(
            subject=subject,
            sender=sender,
            date=received or "",
            preview=" ".join(preview_lines[:3])[:300],
        )

