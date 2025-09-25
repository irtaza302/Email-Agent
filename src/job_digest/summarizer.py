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

    def generate_summary(self) -> tuple[str, list[dict]]:
        """Fetch job messages and generate a summary text."""

        messages = self._gmail_client.fetch_recent_messages(
            timeframe_hours=self._timeframe_hours,
            max_results=self._max_emails,
        )
        if not messages:
            logger.info("No recent emails found in timeframe")
            return ("No job-related emails found in the selected timeframe.", [])

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
            return (classification.summary, [])

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
            return (classification.summary, [])

        summary = self._openrouter_client.summarize_messages(snippets=snippets)
        return summary, relevant_messages

    def _format_snippet(
        self, *, subject: str, sender: str, received: str | None, body: str
    ) -> str:
        received_str = received or ""
        preview = body[:500]
        return (
            f"Subject: {subject}\nFrom: {sender}\nDate: {received_str}\nBody Preview:\n{preview}"
        )

