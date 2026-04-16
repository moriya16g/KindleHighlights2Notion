# Kindle Highlights → Notion

[日本語版 README はこちら](README.ja.md)

A web app that extracts your Kindle highlights and sends them to a Notion database.

## How It Works

```
[Kindle Notebook page] → Bookmarklet extracts highlights from DOM
         ↓ (POST)
[Python HTTP Server]   → Proxies to Notion API
         ↓
[Notion Database]
```

1. You log in to [Kindle Notebook](https://read.amazon.co.jp/notebook) as usual
2. Click a bookmarklet to extract highlights from the page
3. Review highlights in the web UI, then send to Notion
4. Duplicate highlights are automatically skipped on subsequent runs

## Quick Start

```bash
# Clone the repository
git clone https://github.com/<your-username>/kindle-highlights-notion.git
cd kindle-highlights-notion

# (Optional) Create a .env file from the template
cp .env.example .env

# Start the server
python server.py
```

Open http://localhost:8000 in your browser.

## Setup

### 1. Notion Preparation

1. Go to [Notion Integrations](https://www.notion.so/my-integrations) and create an Internal Integration
2. Create a database with these properties (recommended):

   | Property | Type |
   |----------|------|
   | Name | Title |
   | Book | Text |
   | Author | Text |
   | Location | Text |
   | Color | Select |

3. Connect the Integration to your database (Share → Invite)

### 2. Configure the App

1. Open http://localhost:8000
2. Enter your Notion API key and Database ID
3. Click "Test Connection" to verify

### 3. Extract Highlights

1. Open [Kindle Notebook](https://read.amazon.co.jp/notebook) and select a book
2. Click the bookmarklet "📖 Kindle→Fetch"
3. Return to the app to review and send to Notion

## Configuration (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Bind address | `localhost` |
| `PORT` | Port number | `8000` |
| `BASE_URL` | Public URL (for bookmarklet) | auto |
| `BASIC_AUTH_USER` | Basic auth username | (disabled) |
| `BASIC_AUTH_PASS` | Basic auth password | (disabled) |

## Deploy to AWS Lightsail

See [deploy_guide.md](deploy_guide.md) for instructions.

## Tech Stack

- **Backend**: Python standard library only (`http.server`, `urllib`, `json`)
- **Frontend**: Vanilla HTML/CSS/JavaScript (no frameworks)
- **Highlight Extraction**: Bookmarklet (DOM parsing)
- **Deduplication**: SHA256 hash of highlight content
- **i18n**: English / Japanese (switchable in the UI)

## Project Structure

```
├── server.py           # Main server (all-in-one)
├── .env.example        # Configuration template
├── .env                # Your settings (git-ignored)
├── .gitignore
├── deploy_setup.sh     # Lightsail setup script
├── deploy_guide.md     # Deployment guide (EN)
├── deploy_guide.ja.md  # Deployment guide (JA)
├── doc/
│   ├── spec.md         # Specification (JA)
│   └── spec.en.md      # Specification (EN)
├── data/               # Auto-generated, git-ignored
└── static/             # Auto-generated, git-ignored
```

## License

MIT
