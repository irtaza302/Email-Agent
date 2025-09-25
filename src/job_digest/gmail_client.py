"""Gmail API helper functions."""

from __future__ import annotations

import base64
import email
import logging
from pathlib import Path
from typing import Iterable, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import GmailConfig

logger = logging.getLogger(__name__)


class GmailClient:
    """Wrapper around Gmail API for fetching and sending messages."""

    def __init__(self, config: GmailConfig) -> None:
        self._config = config
        self._service = None

    def _get_credentials(self) -> Credentials:
        creds: Optional[Credentials] = None
        if Path(self._config.token_path).exists():
            creds = Credentials.from_authorized_user_file(
                str(self._config.token_path), self._config.scopes
            )

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._config.credentials_path), self._config.scopes
            )
            creds = flow.run_local_server(port=0)

        Path(self._config.token_path).write_text(creds.to_json())
        return creds

    def _get_service(self):
        if self._service is None:
            try:
                creds = self._get_credentials()
                self._service = build("gmail", "v1", credentials=creds)
            except FileNotFoundError as exc:
                logger.error(
                    "Gmail credentials not found. Place credentials.json in config directory."
                )
                raise exc
        return self._service

    def fetch_recent_messages(self, *, timeframe_hours: int, max_results: int) -> list[dict]:
        """Fetch recent Gmail messages within the timeframe (optionally filtered by label)."""

        service = self._get_service()
        query_parts = []
        if self._config.job_label:
            query_parts.append(f"label:{self._config.job_label}")

        query_parts.append(f"newer_than:{timeframe_hours}h")

        query = " ".join(query_parts)
        logger.debug("Gmail query: %s", query)

        try:
            response = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except HttpError as exc:
            logger.exception("Failed to list Gmail messages: %s", exc)
            raise

        messages = response.get("messages", [])
        detailed_messages = []
        for msg in messages:
            try:
                detailed = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )
                detailed_messages.append(detailed)
            except HttpError:
                logger.exception("Failed to fetch message %s", msg["id"])

        return detailed_messages

    @staticmethod
    def _decode_payload(payload_part: dict) -> str:
        data = payload_part.get("body", {}).get("data")
        if not data:
            return ""
        decoded_bytes = base64.urlsafe_b64decode(data)
        return decoded_bytes.decode("utf-8", errors="ignore")

    def extract_message_text(self, message: dict) -> str:
        payload = message.get("payload", {})
        parts = payload.get("parts")
        if parts:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    return self._decode_payload(part)
        body = payload.get("body", {})
        if body and body.get("data"):
            return self._decode_payload({"body": body})
        return ""

    def extract_headers(self, message: dict, names: Iterable[str]) -> dict[str, str]:
        headers = message.get("payload", {}).get("headers", [])
        target_names = {name.lower() for name in names}
        result: dict[str, str] = {}
        for header in headers:
            name = header.get("name", "").lower()
            if name in target_names:
                result[name] = header.get("value", "")
        return result

    def send_email(
        self,
        *,
        sender: str,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
    ) -> None:
        service = self._get_service()

        message = email.message.EmailMessage()
        message["To"] = recipient
        message["From"] = sender
        message["Subject"] = subject
        message.set_content(body_text)
        if body_html:
            message.add_alternative(body_html, subtype="html")

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        try:
            service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()
        except HttpError as exc:
            logger.exception("Failed to send summary email: %s", exc)
            raise

