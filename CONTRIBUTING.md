# Contributing

Thanks for helping improve Open SEO Growth.

## Good First Areas

- Improve beginner setup copy
- Add more URL-only audit checks
- Add tests for opportunity scoring
- Improve empty states and mobile layout
- Add deployment examples
- Add CMS-specific Google setup helpers

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python app.py
```

Open `http://127.0.0.1:8792`.

## Checks

Run these before opening a pull request:

```bash
python -m py_compile app.py seo_growth/*.py
node --check static/app.js
```

## Privacy Rules

Never commit:

- `.env`
- OAuth token files
- analytics exports
- customer URLs, reports, or private screenshots
- API keys or Google client secrets

Use `.env.example` for placeholders only.

## Pull Requests

Keep pull requests focused. Include:

- what changed
- why it changed
- how you tested it
- screenshots for UI changes
