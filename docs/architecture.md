# Architecture

Open SEO Growth is intentionally small:

- Flask serves the app, routes, and JSON APIs.
- The frontend is a single HTML/CSS/JS workbench.
- Google API calls are isolated in `seo_growth/analytics.py`.
- OAuth handling is isolated in `seo_growth/google_oauth.py`.
- URL-only SEO and GEO audit logic is isolated in `seo_growth/instant_audit.py`.
- Opportunity scoring is isolated in `seo_growth/opportunities.py`.

## Request Flow

```text
Browser UI
  -> Flask route in seo_growth/app.py
  -> Instant audit, demo data, or Google API service
  -> JSON response
  -> Frontend render/update
```

## Main Modes

### No-Google Mode

The user enters a URL and receives an instant technical, on-page, and GEO readiness audit. This mode does not require OAuth, GA4, or Search Console.

The audit records the final fetched URL, redirect status, HTTP status, canonical target status, content type, initial HTML response time, HTML payload size, and exact robots.txt access for the audited URL. These signals are included in the SEO score, browser summary, Markdown report, JSON export, and action queue when they fail.

The GEO report is generated from the same fetched HTML. It looks for visible content depth, clear page topic signals, structured data, answer-led sections, trust evidence, freshness dates, external references, search access, and optional `/llms.txt`.

The same evidence also generates a prompt-safe content brief. The brief turns detected gaps into recommended sections, schema guidance, trust guidance, citation guidance, and a writer prompt that explicitly avoids invented rankings, traffic, reviews, prices, credentials, citations, or private analytics data.

The audit API also accepts `{ "demo": true }` and returns a built-in sample audit. This keeps the demo and export workflow available even when the user has no website URL, no Google account, or no network access to a target site.

The frontend can export the current audit from browser state as Markdown, a standalone writer brief, or JSON. These exports are client-side only and do not write reports to disk or the Flask server.

### Setup Assistant Mode

The user sees a one-place Google launcher plus a sandbox demo of the beginner setup journey. This helps validate the product flow before live Google access exists.

The session API also returns platform readiness checks for OAuth credentials, redirect URI shape, local demo mode, hosted HTTPS mode, Flask secret key, and token storage. The frontend renders those checks in the setup assistant and can copy a safe operator checklist.

### Live Google Mode

The user authorizes Google OAuth. The app lists Search Console and GA4 properties, runs reports, and generates SEO opportunities.

The growth dashboard renders the same metrics that can be exported from browser state as Markdown or JSON: source status, clicks, impressions, CTR, average position, organic sessions, revenue, opportunity queues, top queries, top pages, channels, and landing pages.

The action queue export is assembled in the browser from the current audit and growth report. It combines SEO quick wins, GEO quick wins, writer-brief sections, ranking wins, CTR rewrites, and page priorities into CSV or Markdown tasks.

## Token Storage

The starter uses `FileTokenStore` under `instance/oauth_tokens` for local development. This path is ignored by Git.

For hosted multi-user deployments, replace it with encrypted database-backed storage.
