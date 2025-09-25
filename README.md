# Job Email Digest Agent

Daily Gmail digest for job-related emails using OpenRouter summarization.

## Prerequisites
- Python 3.11+
- Google account with Gmail enabled
- Google Cloud project with Gmail API enabled

## Setup
1. Create `.venv` virtual environment and install dependencies:
   ```bash
   cd '/Users/macbook/Documents/My Project/mail agant'
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. Enable Gmail API at Google Cloud console and download OAuth credentials:
   - Create OAuth client ID (Desktop App).
   - Save `credentials.json` into `config/`.

3. Create `.env` with:
   ```
   OPENROUTER_API_KEY=your_openrouter_key
   SUMMARY_RECIPIENT=your_email@example.com
   SUMMARY_SENDER=optional_sender_address
   JOB_LABEL=JobAlerts
   JOB_KEYWORDS=job,interview,offer,recruiter,hiring
   SUMMARY_MODEL=openrouter/anthropic/claude-3.5-sonnet
   SUMMARY_MAX_EMAILS=20
   SUMMARY_TIMEFRAME_HOURS=24
   LOG_LEVEL=INFO
   ```

4. First run (dry-run option does not send email):
   ```bash
   source .venv/bin/activate
   python -m src.main --dry-run
   ```
   Follow browser prompt to authorize Gmail. Token is stored in `config/token.json`.

5. Daily execution:
   ```bash
   source .venv/bin/activate
   python -m src.main
   ```

## Scheduling on macOS
Use `launchd` to run each morning. Example plist (`~/Library/LaunchAgents/com.user.jobdigest.plist`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.user.jobdigest</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd '/Users/macbook/Documents/My Project/mail agant' && source .venv/bin/activate && python -m src.main</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>7</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/macbook/Documents/My Project/mail agant/logs/launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/macbook/Documents/My Project/mail agant/logs/launchd.log</string>
</dict>
</plist>
```
Load with:
```bash
launchctl load ~/Library/LaunchAgents/com.user.jobdigest.plist
```

## Notes
- Gmail label filtering: Create a label (default `JobAlerts`) and apply to relevant emails or adjust keywords.
- Logs stored in `logs/digest.log`.
- Update `.env` to tune summarizer behavior or timeframe.

