"""Command-line entry point for the job email digest."""

from __future__ import annotations

import argparse
import logging
import sys

from job_digest.config import LoggingConfig
from job_digest.digest_service import DigestService


def configure_logging(logging_config: LoggingConfig) -> None:
    logging.basicConfig(
        level=logging_config.level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logging_config.log_dir / "digest.log"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the job email digest")
    parser.add_argument("--dry-run", action="store_true", help="Fetch emails and summarize without sending")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging_config = LoggingConfig()
    logging_config.log_dir.mkdir(exist_ok=True)
    configure_logging(logging_config)

    service = DigestService()

    if args.dry_run:
        logging.info("Running digest in dry-run mode")
        (
            summary_plain,
            messages,
            summary_text_plain,
            summary_html,
        ) = service._summarizer.generate_summary()  # pylint: disable=protected-access
        body_text = service._build_email_body(summary=summary_text_plain, messages=messages)  # pylint: disable=protected-access
        print("Summary:\n", summary_plain)
        print("\nBody preview:\n", body_text)
        if summary_html:
            print("\nHTML preview:\n", summary_html)
        return

    service.run()


if __name__ == "__main__":
    main()

