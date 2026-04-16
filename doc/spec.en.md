# Kindle Highlights → Notion Web App

[日本語版](spec.md)

## Overview
- Log in to the Kindle highlights site (https://read.amazon.co.jp/notebook) and send highlighted text to Notion
- On subsequent runs, only new (unsent) highlights are imported

## Architecture

```
[Kindle Notebook] → Bookmarklet extracts highlights from DOM
       ↓ (POST)
[nginx (HTTPS)]   → [Python HTTP Server] → Notion API
       ↓
[Notion Database]
```

## File Structure

```
├── server.py           # Main server (all-in-one)
├── .env.example        # Configuration template
├── .env                # Local settings (git-ignored)
├── .gitignore
├── deploy_setup.sh     # Lightsail setup script
├── deploy_guide.md     # Deployment guide (EN)
├── deploy_guide.ja.md  # Deployment guide (JA)
├── doc/
│   ├── spec.md         # This specification (JA)
│   └── spec.en.md      # This specification (EN)
├── data/               # Auto-generated (git-ignored)
│   ├── highlights.json
│   ├── sent.json
│   └── config.json
└── static/             # Auto-generated (git-ignored)
    ├── index.html
    ├── style.css
    └── app.js
```

## Local Usage

### 1. Notion Preparation
1. Create an Internal Integration at https://www.notion.so/my-integrations
2. Create a database (recommended properties: Name=title, Book=text, Author=text, Location=text, Color=select)
3. Connect the Integration to the database

### 2. Start the Server
```bash
python server.py
```
→ Open http://localhost:8000

### 3. Extract Highlights
1. Enter Notion API key and Database ID in the web UI
2. Register the bookmarklet in your browser
3. Open Kindle Notebook, select a book → click the bookmarklet
4. Return to the web UI to review → send to Notion

## Deploy to Lightsail

See [deploy_guide.md](../deploy_guide.md)

## Configuration (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| HOST | Bind address | localhost |
| PORT | Port number | 8000 |
| BASE_URL | Public URL for bookmarklet | auto |
| BASIC_AUTH_USER | Basic auth username | (disabled) |
| BASIC_AUTH_PASS | Basic auth password | (disabled) |

## Tech Stack
- **Backend**: Python standard library (`http.server`, `urllib`, `json`)
- **Frontend**: Vanilla HTML/CSS/JavaScript (no frameworks)
- **Highlight Extraction**: Bookmarklet (DOM parsing)
- **Deduplication**: SHA256 hash (`data/sent.json`)
- **Auth**: Basic authentication (for public deployment)
- **Deploy**: AWS Lightsail + nginx + Let's Encrypt
- **i18n**: English / Japanese (switchable in UI)
