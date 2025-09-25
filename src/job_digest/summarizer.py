"""Logic to convert Gmail messages into summaries."""

from __future__ import annotations

import logging

from .gmail_client import GmailClient
from .openrouter_client import OpenRouterClient

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

    def generate_summary(self) -> tuple[str, list[dict]]:
        """Fetch job messages and generate a summary text."""

        messages = self._gmail_client.fetch_job_messages(
            timeframe_hours=self._timeframe_hours,
            max_results=self._max_emails,
        )
        if not messages:
            logger.info("No job messages found in timeframe")
            return ("No job-related emails found in the selected timeframe.", [])

        snippets = []
        enriched_messages = []
        for message in messages:
            text = self._gmail_client.extract_message_text(message)
            headers = self._gmail_client.extract_headers(
                message, ["Subject", "From", "Date"]
            )
            snippets.append(
                self._format_snippet(
                    subject=headers.get("subject", "(No subject)"),
                    sender=headers.get("from", "(Unknown sender)"),
                    received=headers.get("date"),
                    body=text,
                )
            )
            enriched_messages.append({**headers, "body": text})

        summary = self._openrouter_client.summarize_messages(snippets=snippets)
        return summary, enriched_messages

    def _format_snippet(
        self, *, subject: str, sender: str, received: str | None, body: str
    ) -> str:
        received_str = received or ""
        preview = body[:500]
        return (
            f"Subject: {subject}\nFrom: {sender}\nDate: {received_str}\nBody Preview:\n{preview}"
        )

