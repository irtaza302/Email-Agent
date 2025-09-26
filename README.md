# Job Email Digest Agent

Daily Gmail digest for job-related emails using OpenRouter AI summarization. Automatically sends beautifully formatted HTML emails with job alerts, networking opportunities, and relevant updates.

## ✨ Features

- **AI-Powered Summarization**: Uses xAI Grok for intelligent email analysis
- **Smart Filtering**: Automatically identifies job-related emails using advanced classification
- **Beautiful HTML Emails**: Modern, responsive email templates with customizable themes
- **GitHub Actions Integration**: Automated daily execution in the cloud
- **Flexible Configuration**: Extensive customization options via environment variables
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## Prerequisites

- Python 3.11+
- Google account with Gmail enabled
- Google Cloud project with Gmail API enabled
- OpenRouter API key for AI summarization

## 🚀 Quick Setup

### 1. Local Development Setup

1. **Clone and setup environment**:
   ```bash
   cd '/Users/macbook/Documents/My Project/mail agant'
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

2. **Configure Gmail API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Gmail API for your project
   - Create OAuth 2.0 Client ID (Desktop App)
   - Download `credentials.json` and place it in `config/`

3. **Create environment configuration**:
   ```bash
   # .env file
   OPENROUTER_API_KEY=your_openrouter_key
   SUMMARY_RECIPIENT=your_email@example.com
   SUMMARY_SENDER=optional_sender_address
   JOB_KEYWORDS=job,interview,offer,recruiter,hiring
   SUMMARY_MODEL=x-ai/grok-4-fast:free
   SUMMARY_MAX_EMAILS=20
   SUMMARY_TIMEFRAME_HOURS=24
   LOG_LEVEL=INFO
   SUMMARY_TONE=professional
   SUMMARY_FORMAT=markdown
   SUMMARY_THEME_COLOR=#2563eb
   SUMMARY_BG_COLOR=#0f172a
   SUMMARY_HEADER_TITLE=Job Digest
   SUMMARY_HEADER_SUBTITLE=
   ```

4. **Initial authorization**:
   ```bash
   source venv/bin/activate
   python -m src.main --dry-run
   ```
   Follow the browser prompt to authorize Gmail access. Token is saved to `config/token.json`.

5. **Test the digest**:
   ```bash
   python -m src.main --dry-run
   ```

### 2. GitHub Actions Deployment (Recommended)

For automated daily execution, deploy to GitHub Actions:

#### Required GitHub Secrets:
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `SUMMARY_RECIPIENT`: Email address to receive digests
- `SUMMARY_SENDER`: Email address to send from (optional)
- `GCP_CREDENTIALS_B64`: Base64-encoded full OAuth credentials JSON
- `GCP_TOKEN_B64`: Base64-encoded OAuth access token

#### Optional GitHub Variables:
- `JOB_LABEL`: Gmail label to filter emails (leave empty for no filtering)
- `SUMMARY_MODEL`: AI model to use (default: x-ai/grok-4-fast:free)
- `SUMMARY_MAX_EMAILS`: Maximum emails to process (default: 20)
- `SUMMARY_TIMEFRAME_HOURS`: Hours to look back (default: 24)
- `LOG_LEVEL`: Logging level (default: INFO)
- `SUMMARY_TONE`: Email tone (default: professional)
- `SUMMARY_FORMAT`: Summary format (default: markdown)
- `SUMMARY_THEME_COLOR`: HTML theme color (default: #2563eb)
- `SUMMARY_BG_COLOR`: HTML background color (default: #0f172a)
- `SUMMARY_HEADER_TITLE`: Email header title (default: Job Digest)

#### Generate Base64 Secrets:
```bash
# For GCP_CREDENTIALS_B64 (full token.json)
base64 -i config/token.json

# For GCP_TOKEN_B64 (just the token field)
python3 -c "import json, base64; data=json.load(open('config/token.json')); print(base64.b64encode(data['token'].encode()).decode())"
```

The workflow runs daily at 11 AM UTC and can also be triggered manually.

## 📧 Email Categories

The digest automatically categorizes emails into:
- **Job Alerts and Opportunities**: New positions, applications, offers
- **Networking**: Connection requests, professional contacts
- **Resources**: Job search tips, newsletters, career advice
- **Interviews & Deadlines**: Important scheduling and time-sensitive items

## 🎨 Customization

### Email Themes
Customize the HTML email appearance:
- `SUMMARY_THEME_COLOR`: Primary accent color
- `SUMMARY_BG_COLOR`: Background color
- `SUMMARY_HEADER_TITLE`: Main header text
- `SUMMARY_HEADER_SUBTITLE`: Subtitle text

### AI Configuration
- `SUMMARY_MODEL`: Choose different AI models (xAI Grok, Claude, GPT, etc.)
- `SUMMARY_TONE`: professional, casual, formal
- `SUMMARY_FORMAT`: markdown, plain text

### Filtering Options
- `JOB_LABEL`: Filter by Gmail label (leave empty for all emails)
- `SUMMARY_TIMEFRAME_HOURS`: How far back to search
- `SUMMARY_MAX_EMAILS`: Maximum emails to process

## 📊 Monitoring

### Logs
- Local logs: `logs/digest.log`
- GitHub Actions: View in Actions tab → Workflow runs → Logs

### Troubleshooting
- Use `--dry-run` flag for testing without sending emails
- Check Gmail API quotas and token validity
- Verify OpenRouter API key and credits

## 🔧 Advanced Usage

### Manual Scheduling (macOS)
Use `launchd` for local scheduling:

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
    <string>cd '/Users/macbook/Documents/My Project/mail agant' && source venv/bin/activate && python -m src.main</string>
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

Load with: `launchctl load ~/Library/LaunchAgents/com.user.jobdigest.plist`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `--dry-run`
5. Submit a pull request

## 📝 License

This project is open source. Feel free to use and modify as needed.

