# Open SEO Growth

Beginner-ready SEO and GEO onboarding, Google setup, and growth analytics in one small Flask app.

Open SEO Growth is my first open-source project as a beginner learning with vibe coding. Feedback, issues, ideas, and suggestions are very welcome. Thank you for taking a look.

Open SEO Growth helps a site owner answer a practical question:

> "What can I improve now, and how do I connect Google data when I am ready?"

It starts with a URL-only SEO and GEO audit that works without GA4 or Search Console. When Google access exists, it connects through OAuth, discovers Search Console and GA4 properties, and turns clicks, impressions, CTR, average position, sessions, and channel mix into prioritized growth actions.

![Open SEO Growth running locally](docs/assets/open-seo-growth-dashboard.png)

## What It Does

- Instant URL audit with no Google setup
- GEO readiness scan for crawlable text, answer structure, schema, trust signals, references, and optional `llms.txt`
- Client-ready Markdown export and JSON evidence export from the browser
- Built-in sample audit for demos without network, Google, or a real website
- No-Google starter report for beginners
- Clickable sandbox flow for the Google setup journey
- Google OAuth connection flow
- Automatic Search Console property discovery
- Automatic GA4 property discovery
- Search Console clicks, impressions, CTR, and average position
- GA4 sessions, landing pages, channel mix, events, and revenue signals
- Ranking opportunities, CTR rewrite queue, page priority queue, and ranking distribution
- Sample data mode for demos and product validation

## Who It Is For

- Solo founders who know their website URL but not GA4
- SEO consultants who need a simple onboarding flow for clients
- Agencies that want a lightweight open-source growth dashboard starter
- Developers building a hosted SEO analytics product
- Self-hosters who want to connect their own Google properties

## Product Flow

1. Enter a website URL and run the instant audit.
2. Review technical, on-page, and AI answer readiness gaps.
3. Export the SEO/GEO report as Markdown or JSON evidence.
4. Use the setup assistant or sandbox demo if Google is not ready.
5. Connect Google when OAuth, GA4, and Search Console access exist.
6. Run the growth report and turn data into an action queue.

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

You can use Instant audit, Load sample audit, Setup assistant, Sandbox demo, and Load sample growth without Google OAuth.

The audit screen can export:

- a client-ready Markdown report
- raw JSON audit evidence
- a clipboard-ready Markdown brief

## GEO Readiness

The instant audit includes a Generative Engine Optimization readiness report. It checks whether a page is understandable, structured, and citable enough for AI answer surfaces:

- crawlable visible content
- clear title and H1 topic signals
- structured data types such as `Organization`, `WebSite`, `Article`, `Product`, `FAQPage`, or `HowTo`
- question or answer-oriented sections
- trust signals such as author, organization, about, contact, privacy, sources, or editorial references
- external references where appropriate
- indexability and robots access
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

## Environment

```env
FLASK_SECRET_KEY=change-me
APP_BASE_URL=http://127.0.0.1:8792
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8792/auth/google/callback
TOKEN_STORE_DIR=instance/oauth_tokens
ALLOW_INSECURE_OAUTH=1
ANALYTICS_REPORT_DAYS=30
ANALYTICS_DATA_LAG_DAYS=2
GSC_OPPORTUNITY_MIN_IMPRESSIONS=20
```

Use `ALLOW_INSECURE_OAUTH=1` only for local HTTP development. Cloud deployments should use HTTPS and remove it.

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
  templates/
    index.html                 Single-page workbench UI
  static/
    app.js                     Frontend state and interactions
    styles.css                 Product UI styles
    assets/                    Logo and social preview
  docs/
    beginner-google-setup.md   Beginner flow and launcher model
    geo-readiness.md           GEO scoring model and limits
    google-api-notes.md        Google API details
    product-assets.md          Product copy and design notes
```

## API Endpoints

- `GET /api/session`
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

The bundled `FileTokenStore` is fine for local demos and private prototypes. A public multi-user deployment should replace it with encrypted database-backed token storage plus user accounts, workspace membership, rate limiting, and stronger OAuth state handling.

## Roadmap

- Saved sites and saved report history
- Prompt-safe page briefs for writers
- Database-backed encrypted OAuth token storage
- User accounts and team workspaces
- Hosted SaaS mode with a platform-owned OAuth client
- CMS-specific setup helpers for common website builders
- Background report caching and scheduled re-checks
- More technical SEO checks and schema validation

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), open an issue for larger changes, and avoid committing real analytics data or OAuth tokens.

## License

MIT. See [LICENSE](LICENSE).
