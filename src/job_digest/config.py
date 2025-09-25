"""Configuration helpers for the job email digest agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class GmailConfig:
    scopes: Tuple[str, ...] = (
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    )
    credentials_path: Path = ROOT_DIR / "config" / "credentials.json"
    token_path: Path = ROOT_DIR / "config" / "token.json"
    job_label: Optional[str] = os.getenv("JOB_LABEL") or None


@dataclass(frozen=True)
class SummaryConfig:
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    model: str = os.getenv("SUMMARY_MODEL", "x-ai/grok-4-fast:free")
    max_emails: int = int(os.getenv("SUMMARY_MAX_EMAILS", "20"))
    timeframe_hours: int = int(os.getenv("SUMMARY_TIMEFRAME_HOURS", "24"))
    summary_recipient: str | None = os.getenv("SUMMARY_RECIPIENT")
    summary_sender: str | None = os.getenv("SUMMARY_SENDER")
    openrouter_api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    user_agent: str = "job-email-digest/0.1"
    summarizer_tone: str = os.getenv("SUMMARY_TONE", "professional")
    summarizer_format: str = os.getenv("SUMMARY_FORMAT", "markdown")
    html_theme_color: str = os.getenv("SUMMARY_THEME_COLOR", "#2563eb")
    html_background_color: str = os.getenv("SUMMARY_BG_COLOR", "#0f172a")
    html_header_title: str = os.getenv("SUMMARY_HEADER_TITLE", "Job Digest")
    html_header_subtitle: str = os.getenv("SUMMARY_HEADER_SUBTITLE", "")


@dataclass(frozen=True)
class LoggingConfig:
    log_dir: Path = ROOT_DIR / "logs"
    level: str = os.getenv("LOG_LEVEL", "INFO")

