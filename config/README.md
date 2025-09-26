# Configuration Files

This directory should contain your Gmail API credentials. These files are **not included** in the repository for security reasons.

## Required Files

### `credentials.json`
- Download from [Google Cloud Console](https://console.cloud.google.com/)
- Create OAuth 2.0 Client ID (Desktop App)
- Place the downloaded file here as `credentials.json`

### `token.json`
- Generated automatically during first run
- Contains OAuth access and refresh tokens
- Will be created when you run the application for the first time

## Setup Process

1. Get `credentials.json` from Google Cloud Console
2. Run the application - it will prompt for authorization and create `token.json`
3. For GitHub Actions deployment, encode these files as base64 secrets

## Security Note

These files contain sensitive authentication information and are excluded from version control via `.gitignore`. Never commit them to the repository.
