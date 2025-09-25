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
            summary_text, messages, summary_text_plain, summary_html = self._summarizer.generate_summary()
            subject = f"Daily Job Digest – {datetime.now().strftime('%Y-%m-%d')}"
            body_text = self._build_email_body(summary=summary_text_plain, messages=messages)
            body_html = self._build_email_body_html(
                summary_html or summary_text_plain,
                messages=messages,
                theme_color=self._summary_config.html_theme_color,
                background_color=self._summary_config.html_background_color,
                header_title=self._summary_config.html_header_title,
                header_subtitle=self._summary_config.html_header_subtitle,
            )

            self._gmail_client.send_email(
                sender=self._summary_config.summary_sender
                or self._summary_config.summary_recipient,
                recipient=self._summary_config.summary_recipient,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
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

    def _build_email_body_html(
        self,
        summary: str,
        messages: list[dict],
        *,
        theme_color: str,
        background_color: str,
        header_title: str,
        header_subtitle: str,
    ) -> str:
        items_html = []
        for message in messages:
            preview = (message.get("body", "") or "").strip().replace("\n", " ")
            preview = preview[:320]
            items_html.append(
                """
                <li style="margin:0 0 0.85em;">
                  <div style="padding:0.65em 0.75em; background:#0f172a0d; border-radius:10px;">
                    <p style="margin:0; font-weight:600; color:#0f172a;">{subject}</p>
                    <p style="margin:0.2em 0 0; font-size:0.85em; color:#475569;">{sender} • {date}</p>
                    {preview_block}
                  </div>
                </li>
                """.format(
                    subject=message.get("subject", "(No subject)"),
                    sender=message.get("from", "(Unknown sender)"),
                    date=message.get("date", ""),
                    preview_block=(
                        f"<p style=\"margin:0.45em 0 0; color:#475569; line-height:1.5;\">{preview}</p>"
                        if preview
                        else ""
                    ),
                )
            )

        items_html_str = "\n".join(items_html) or "<li>No individual emails were highlighted.</li>"
        return f"""
        <html>
          <body style="margin:0; padding:0; background:{background_color}; font-family:'Inter', 'Segoe UI', sans-serif; color:#0f172a;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px 40px;">
              <tr>
                <td align="center">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:680px; background:#ffffff; border-radius:18px; overflow:hidden; box-shadow:0 24px 48px rgba(15,23,42,0.15);">
                    <tr>
                      <td style="background:#ffffff; padding:28px 32px 12px;">
                        <div style="display:flex; align-items:center; justify-content:center; gap:12px;">
                          <div style="width:8px; height:40px; border-radius:999px; background:{theme_color};"></div>
                          <div>
                            <p style="margin:0; font-size:12px; letter-spacing:0.18em; text-transform:uppercase; color:#94a3b8;">{header_title}</p>
                            <h1 style="margin:6px 0 0; font-size:24px; font-weight:600; color:#0f172a;">{header_subtitle or datetime.now().strftime('%A, %B %d, %Y')}</h1>
                          </div>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:24px 32px 28px;">
                        <div style="border:1px solid #e2e8f0; border-radius:14px; padding:18px 20px; margin-bottom:22px; background:#f8fafc;">
                          <h2 style="margin:0 0 12px; font-size:18px; color:{theme_color};">Summary</h2>
                          <div style="white-space: pre-wrap; line-height:1.7; font-size:15px; color:#1e293b;">{summary}</div>
                        </div>
                        <h2 style="margin:0 0 12px; font-size:18px; color:{theme_color};">Emails Included</h2>
                        <ul style="padding-left:0; margin:0; list-style:none;">{items_html_str}</ul>
                        <p style="margin:24px 0 0; font-size:12px; color:#94a3b8; text-align:center;">
                          Generated automatically by your job email agent. Manage settings in your configuration file.
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """.strip()

