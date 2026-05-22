# Open SEO Growth

Open SEO Growth is a small, deployable SEO onboarding and growth workbench. It is designed for two very different users:

- beginners who only know their website URL
- operators who already have GA4 and Google Search Console access

The product flow is:

1. Run an instant URL audit with no Google setup.
2. Connect Google when the user wants verified traffic/search data.
3. Auto-discover GA4 and Search Console properties.
4. Turn clicks, impressions, CTR, ranking, and sessions into an action queue.

The project extracts the growth-analysis and connection setup workflow into a standalone open-source app:

- Instant URL audit
- Google OAuth connection
- Automatic Search Console property discovery
- Automatic GA4 property discovery
- Clicks, impressions, CTR, average position
- GA4 sessions, Organic Search sessions, landing pages, channel mix
- Ranking opportunities, CTR rewrite queue, page priority queue, ranking distribution

The app intentionally avoids private client data, proprietary keyword banks, and private knowledge-base logic.

## Quick Start

```powershell
git clone https://github.com/Lumo016/open-seo-growth.git
cd open-seo-growth
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python app.py
```

On macOS or Linux, use `python3 -m venv .venv`, `source .venv/bin/activate`, and `pip install -r requirements.txt`.

Open `http://127.0.0.1:8792`.

You can run `Instant audit` or click `Load sample data` without OAuth. Live clicks, impressions, rankings, and sessions require Google OAuth.

## Beginner User Journey

If the user has never heard of GA4 or Search Console, do not block them. The app should start with a URL scan.

Supported without Google:

- HTTP status
- title and meta description
- H1
- canonical
- robots meta
- robots.txt
- sitemap.xml
- image alt coverage
- internal/external links
- structured data hints
- GA4/GTM tag detection hints

Supported after Google connection:

- Search Console clicks, impressions, CTR, and average position
- GA4 sessions, users, engagement, landing pages, channels, and ecommerce events
- ranking opportunities and missed-click estimates

## Google Cloud Setup

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

The app then calls Search Console `sites.list` and GA4 Admin `accountSummaries.list` to auto-fill the selectors.

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

Set `ALLOW_INSECURE_OAUTH=1` only for local HTTP development. Cloud deployments should use HTTPS and remove it.

## Security And Privacy

Do not commit `.env`, OAuth token files, analytics exports, or customer reports. The repository includes only `.env.example` placeholders. Runtime token files are written under `instance/`, which is ignored by Git.

## Production Notes

This starter stores OAuth tokens in `instance/oauth_tokens` keyed by a Flask session id. That is fine for local development and a private prototype, but for a public multi-tenant deployment you should replace `FileTokenStore` with a database-backed encrypted token store.

Recommended production additions:

- Encrypted token storage
- User accounts
- OAuth state hardening and account identity display
- Team/workspace membership
- Rate limiting
- Background report caching
- Per-site saved reports
- Exportable action tasks

## SaaS Mode vs Self-Host Mode

For a hosted SaaS, the platform owner should configure Google OAuth once. End users should only click `Connect Google`.

For self-hosting, each deployer creates their own Google OAuth client and fills `.env`.

This split keeps the beginner experience simple while preserving an open-source path for technical users.

## API Shape

- `GET /api/session`
- `GET /auth/google/start`
- `GET /auth/google/callback`
- `POST /auth/logout`
- `POST /api/audit`
- `GET /api/connections`
- `POST /api/analyze`

`POST /api/audit` accepts:

```json
{
  "url": "https://example.com"
}
```

`POST /api/analyze` accepts:

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

## Measurement Model

Search Console is the source of truth for Google query clicks, impressions, CTR, and average position. GA4 is the source of truth for sessions, channel mix, landing pages, engagement, and ecommerce events.

Opportunity scoring uses:

- GSC impressions
- average position
- current CTR
- a practical expected CTR curve
- estimated missed clicks

It is a prioritization model, not a ranking guarantee.
