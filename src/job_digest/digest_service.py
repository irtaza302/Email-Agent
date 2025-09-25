"""Service orchestrating the daily digest flow."""

from __future__ import annotations

import logging
from datetime import datetime

from googleapiclient.errors import HttpError

from .config import GmailConfig, LoggingConfig, SummaryConfig
from .gmail_client import GmailClient
from .summarizer import JobEmailSummarizer
from .openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class DigestService:
    """Main entry point for generating and emailing the digest."""

    def __init__(self) -> None:
        self._gmail_config = GmailConfig()
        self._summary_config = SummaryConfig()
        self._logging_config = LoggingConfig()

        if not self._summary_config.summary_recipient:
            raise ValueError("SUMMARY_RECIPIENT must be set in environment variables")

        self._gmail_client = GmailClient(self._gmail_config)
        self._openrouter_client = OpenRouterClient(self._summary_config)
        self._summarizer = JobEmailSummarizer(
            gmail_client=self._gmail_client,
            openrouter_client=self._openrouter_client,
            max_emails=self._summary_config.max_emails,
            timeframe_hours=self._summary_config.timeframe_hours,
        )

    def run(self) -> None:
        logger.info("Running daily digest service")
        try:
            summary, messages = self._summarizer.generate_summary()
            subject = f"Daily Job Digest – {datetime.now().strftime('%Y-%m-%d')}"
            body = self._build_email_body(summary=summary, messages=messages)

            self._gmail_client.send_email(
                sender=self._summary_config.summary_sender
                or self._summary_config.summary_recipient,
                recipient=self._summary_config.summary_recipient,
                subject=subject,
                body=body,
            )
            logger.info("Digest email sent to %s", self._summary_config.summary_recipient)
        except HttpError as exc:
            logger.exception("Gmail API error during digest run: %s", exc)
            raise

    def _build_email_body(self, *, summary: str, messages: list[dict]) -> str:
        lines = ["Daily Job Email Digest", "", "Summary:", summary, "", "Emails included:"]
        for message in messages:
            lines.append("-")
            lines.append(f"Subject: {message.get('subject', '(No subject)')}")
            lines.append(f"From: {message.get('from', '(Unknown sender)')}")
            lines.append(f"Date: {message.get('date', '')}")
            if message.get("body"):
                lines.append("Preview:")
                lines.append(message["body"][:280])
            lines.append("")
        return "\n".join(lines)

