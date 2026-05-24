# Open SEO Growth

A runnable open-source Flask app for instant SEO/GEO audits, beginner Google setup, and GA4/Search Console growth analysis.

Open SEO Growth is my first open-source project as a beginner learning with vibe coding. Feedback, issues, ideas, and suggestions are very welcome. Thank you for taking a look.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Lumo016/open-seo-growth)

Open SEO Growth helps a site owner answer a practical question:

> "What can I run right now, before I understand GA4 or Search Console?"

The app starts with a URL-only SEO and GEO audit that works without Google setup. When Google access exists, it can connect through OAuth, discover Search Console and GA4 properties, and turn clicks, impressions, CTR, average position, sessions, and channel mix into prioritized growth actions.

Runtime screenshot captured from the running Flask app after loading the sample audit and sample growth report:

![Open SEO Growth running locally](docs/assets/open-seo-growth-dashboard.png)

## What You Can Run Today

- Instant URL audit with no Google setup, including HTTP status, canonical target, sitemap coverage, X-Robots-Tag, response timing, HTML payload, and exact robots.txt access evidence
- GEO readiness scan for crawlable text, answer structure, schema types, JSON-LD parse errors, trust signals, freshness, references, and optional `llms.txt`
- Prompt-safe GEO writer brief generated from audit evidence
- Client-ready Markdown export and JSON evidence export from the browser, including technical response evidence
- Browser-local recent audit history so a user can reopen the latest URL scans without a database
- Built-in sample audit for demos without network, Google, or a real website
- Browser-local CSV import for exported Search Console and GA4 rows when OAuth is not configured
- Public URL scan guardrails that block private, local, non-web, credentialed, and non-standard-port audit targets
- Built-in anonymous audit rate limiting for free-tier-friendly public trials
- Productized No-Google starter report and proposal export for beginners without analytics access
- Clickable sandbox flow for the Google setup journey
- Copyable beginner Google setup plan for users without GA4 or Search Console
- Platform readiness checklist for OAuth, redirect URI, HTTPS mode, secret key, and token storage
- Google OAuth connection flow
- Automatic Search Console property discovery
- Automatic GA4 property discovery
- Search Console clicks, impressions, CTR, and average position
- GA4 sessions, landing pages, channel mix, events, and revenue signals
- Ranking opportunities, CTR rewrite queue, page priority queue, and ranking distribution
- Client-ready growth report export for Search Console and GA4 metrics
- CSV and Markdown action queue export for implementation handoff
- Sample growth dashboard mode for demos and product validation
- `/healthz` endpoint and Dockerfile for free-tier-friendly hosting experiments
- Built-in `/robots.txt`, `/sitemap.xml`, and `/llms.txt` for hosted app discovery
- Dynamic canonical, social sharing metadata, and SoftwareApplication JSON-LD for the app itself
- Public Privacy Policy and Terms Of Service pages for OAuth and user trust readiness
- Optional encrypted file storage for Google OAuth tokens during hosted trials
- `render.yaml` Blueprint for a one-service Render trial deployment

## Local Demo

After starting the app, open `http://127.0.0.1:8792` and try these controls:

1. Click `Load sample audit` to see the SEO/GEO audit without entering a URL.
2. Click `Run instant audit` after entering a real public URL.
3. Click `Copy Markdown`, `Download .md`, `Download brief`, `Copy proposal`, `Download proposal`, or `Download .json` after an audit runs.
4. Reopen or clear saved scans from `Recent audits`. This history stays in the current browser only.
5. Click `Start demo setup` in the Google setup assistant to walk through the beginner flow.
6. Click `Copy beginner plan` or `Download plan` for a plain-English GA4/Search Console setup handoff.
7. Copy the platform readiness checklist before configuring a hosted Google connection.
8. Click `Load sample CSV` or import exported Search Console / GA4 CSV files to build a growth report without OAuth.
9. Click `Load sample growth` to see the growth dashboard without Google OAuth.
10. Export the growth report as Markdown or JSON after sample, imported CSV, or live Google data loads.
11. Export the action queue as CSV or Markdown for client, writer, or developer handoff.
12. Click `Connect Google` only when you have a Google Cloud OAuth client and access to real GA4/Search Console properties.

## Quick Start

```bash
git clone https://github.com/Lumo016/open-seo-growth.git
cd open-seo-growth
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python app.py
```

On macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open:

```text
http://127.0.0.1:8792
```

You can use Instant audit, Load sample audit, Recent audits, CSV import, Setup assistant, Sandbox demo, and Load sample growth without Google OAuth.

## Container Demo

You can also run the app as a small container for hosting experiments:

```bash
docker build -t open-seo-growth .
docker run --rm -p 8792:8792 --env-file .env open-seo-growth
```

Then check:

```text
http://127.0.0.1:8792/healthz
```

For public hosting, set `APP_BASE_URL` and `GOOGLE_REDIRECT_URI` to the final HTTPS domain before enabling Google OAuth for users.

## Render Trial Deploy

The repository includes `render.yaml` for a one-service Docker deployment on Render:

- Docker runtime
- web service health check at `/healthz`
- generated Flask secret key
- generated token encryption key
- automatic `RENDER_EXTERNAL_URL` detection for the public app URL
- anonymous audit rate limiting enabled
- no database required for the sample audit, live URL audit, setup assistant, or sample growth report

After deployment, the app uses Render's `RENDER_EXTERNAL_URL` as its public base URL when `APP_BASE_URL` is not set. Set `APP_BASE_URL` only when you add a custom domain or need to override the detected URL. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` only when you are ready to test live Search Console and GA4 OAuth.

See [docs/render-deployment.md](docs/render-deployment.md).

The audit screen can export:

- a client-ready Markdown report
- a standalone GEO content brief for writers
- raw JSON audit evidence
- a clipboard-ready Markdown report

The growth dashboard can export:

- a client-ready Markdown growth report
- raw JSON growth evidence
- a clipboard-ready Markdown growth summary

The action queue can export:

- CSV tasks for spreadsheets or project management tools
- Markdown tasks for client handoff or issue creation

## Development Checks

```bash
pip install -r requirements-dev.txt
python -m py_compile app.py seo_growth/*.py
python -m pytest -q
node --check static/app.js
```

## GEO Readiness

The instant audit includes a Generative Engine Optimization readiness report. It checks whether a page is understandable, structured, and citable enough for AI answer surfaces:

- crawlable visible content
- clear title and H1 topic signals
- structured data types such as `Organization`, `WebSite`, `Article`, `Product`, `FAQPage`, or `HowTo`
- question or answer-oriented sections
- trust signals such as author, organization, about, contact, privacy, sources, or editorial references
- published or updated date signals
- external references where appropriate
- indexability, robots meta, X-Robots-Tag, exact robots.txt URL access, and sitemap URL coverage
- optional `/llms.txt`

This score is a heuristic, not a guarantee of AI citation, inclusion, or ranking. See [docs/geo-readiness.md](docs/geo-readiness.md).

## Google Setup

Live Google metrics require a Google Cloud OAuth client and user access to the target GA4 and Search Console properties.

1. Create a Google Cloud project.
2. Enable these APIs:
   - Google Search Console API
   - Google Analytics Data API
   - Google Analytics Admin API
3. Create an OAuth client:
   - Application type: Web application
   - Local redirect URI: `http://127.0.0.1:8792/auth/google/callback`
   - Cloud redirect URI: `https://your-domain.com/auth/google/callback`
4. Copy the client ID and secret into `.env`.
5. Make sure the signing Google account has:
   - Search Console access to the site property
   - GA4 Viewer access to the property

The app then calls Search Console `sites.list` and GA4 Admin `accountSummaries.list` to fill the property selectors.

The setup assistant includes a platform readiness checklist. It shows whether the current deployment is ready for local OAuth testing, whether hosted HTTPS mode is configured, and why file-based token storage must be replaced before multi-user SaaS hosting.

## Environment

```env
FLASK_SECRET_KEY=change-me
APP_BASE_URL=http://127.0.0.1:8792
RENDER_EXTERNAL_URL=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8792/auth/google/callback
TOKEN_STORE_DIR=instance/oauth_tokens
TOKEN_ENCRYPTION_KEY=
ALLOW_INSECURE_OAUTH=1
ANALYTICS_REPORT_DAYS=30
ANALYTICS_DATA_LAG_DAYS=2
GSC_OPPORTUNITY_MIN_IMPRESSIONS=20
AUDIT_RATE_LIMIT_PER_HOUR=30
```

If `APP_BASE_URL` is empty, the app falls back to `RENDER_EXTERNAL_URL`, then local development. `GOOGLE_REDIRECT_URI` defaults to `{APP_BASE_URL}/auth/google/callback` when it is empty.

Use `ALLOW_INSECURE_OAUTH=1` only for local HTTP development. Cloud deployments should use HTTPS and remove it.

Set `AUDIT_RATE_LIMIT_PER_HOUR` to a practical number for anonymous public scans. Use `0` only for private local experiments.

Set `TOKEN_ENCRYPTION_KEY` to any long random secret before storing real Google OAuth tokens. The starter derives an encryption key from it and encrypts token files at rest. Keep the value stable across deploys or previously saved tokens cannot be decrypted.

## Project Structure

```text
open-seo-growth/
  app.py                       Flask entrypoint
  seo_growth/
    app.py                     Routes and API endpoints
    analytics.py               Google API calls and demo report
    config.py                  Environment settings
    google_oauth.py            OAuth flow and local token store
    instant_audit.py           URL-only SEO and GEO readiness audit
    opportunities.py           SEO opportunity scoring
    rate_limit.py              In-memory anonymous audit limiter
  templates/
    index.html                 Single-page workbench UI
  static/
    app.js                     Frontend state and interactions
    styles.css                 Product UI styles
    assets/                    Logo
  tests/                       Pytest coverage for audit and API behavior
  render.yaml                  Render Blueprint for a one-service Docker trial deploy
  docs/
    beginner-google-setup.md   Beginner flow and launcher model
    csv-import.md              Search Console and GA4 CSV import guide
    geo-readiness.md           GEO scoring model and limits
    google-api-notes.md        Google API details
    render-deployment.md       Render deployment notes
    runtime-demo.md            Runtime screenshot and demo verification notes
```

## API Endpoints

- `GET /api/session`
- `GET /robots.txt`
- `GET /sitemap.xml`
- `GET /llms.txt`
- `GET /healthz`
- `GET /privacy`
- `GET /terms`
- `GET /auth/google/start`
- `GET /auth/google/callback`
- `POST /auth/logout`
- `POST /api/audit`
- `GET /api/connections`
- `POST /api/analyze`

Run URL audit:

```json
{
  "url": "https://example.com"
}
```

Run the built-in sample audit:

```json
{
  "demo": true
}
```

Run live or demo analysis:

```json
{
  "gsc_site_url": "https://example.com/",
  "ga4_property_id": "123456789",
  "target_url": "https://example.com/blog/page",
  "days": 30,
  "lag_days": 2
}
```

Use `"demo": true` to load seeded demo data.

## Security And Privacy

Do not commit `.env`, OAuth token files, analytics exports, customer reports, or private site data. The repository includes only `.env.example` placeholders. Runtime token files are written under `instance/`, which is ignored by Git.

The public URL audit blocks private network targets, localhost, non-web schemes, embedded URL credentials, and non-standard web ports before making outbound requests. Redirect targets are checked as well. Anonymous live audits are rate limited in-process by client address. This is a necessary guardrail for a hosted scanner, but production deployments should still use network egress controls and platform-level rate limiting.

The bundled `FileTokenStore` is fine for local demos and private single-user trials. Set `TOKEN_ENCRYPTION_KEY` for hosted trials so token files are encrypted at rest. A public multi-user deployment should replace it with encrypted database-backed token storage plus user accounts, workspace membership, rate limiting, and stronger OAuth state handling.

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), open an issue for larger changes, and avoid committing real analytics data or OAuth tokens.

## License

MIT. See [LICENSE](LICENSE).
