# Architecture

Open SEO Growth is intentionally small:

- Flask serves the app, routes, and JSON APIs.
- The frontend is a single HTML/CSS/JS workbench.
- Google API calls are isolated in `seo_growth/analytics.py`.
- OAuth handling is isolated in `seo_growth/google_oauth.py`.
- URL-only SEO and GEO audit logic is isolated in `seo_growth/instant_audit.py`.
- Anonymous live audit rate limiting is isolated in `seo_growth/rate_limit.py`.
- Opportunity scoring is isolated in `seo_growth/opportunities.py`.
- `/healthz` exposes a minimal platform health check without secrets or user data.
- `/robots.txt`, `/sitemap.xml`, and `/llms.txt` are generated from the configured public base URL.
- The homepage renders canonical, Open Graph, Twitter card, and SoftwareApplication JSON-LD metadata from the same public base URL.
- `/privacy` and `/terms` explain Google data handling, storage limits, acceptable use, and open-source terms.
- `FileTokenStore` can encrypt OAuth token files when `TOKEN_ENCRYPTION_KEY` is configured.
- Basic security response headers are added to every response.

## Request Flow

```text
Browser UI
  -> Flask route in seo_growth/app.py
  -> Instant audit, demo data, or Google API service
  -> JSON response
  -> Frontend render/update
```

The homepage includes a client-side `Start here` path selector. It does not add a new backend mode; it routes the user to the existing URL audit, CSV import, Google setup assistant, or a complete sample workspace that loads the built-in audit plus browser-local sample CSV growth report.

## Main Modes

### No-Google Mode

The user enters a URL and receives an instant technical, on-page, and GEO readiness audit. This mode does not require OAuth, GA4, or Search Console.

The audit records the final fetched URL, redirect status, HTTP status, canonical target status, sitemap URL coverage, X-Robots-Tag status, JSON-LD parse status, content type, initial HTML response time, HTML payload size, and exact robots.txt access for the audited URL. These signals are included in the SEO score, browser summary, Markdown report, JSON export, and action queue when they fail.

Before fetching a submitted URL, the audit validates that the target is a public HTTP(S) website on standard web ports. It rejects localhost, private networks, embedded credentials, non-web schemes, and unsafe redirect destinations. Hosted deployments should still pair this with rate limits and host-level egress controls.

Live URL scans pass through an in-memory per-client rate limiter before the network request starts. Built-in sample audit requests skip the limiter because they do not make outbound requests.

The GEO report is generated from the same fetched HTML. It looks for visible content depth, clear page topic signals, structured data, answer-led sections, trust evidence, freshness dates, external references, search access, and optional `/llms.txt`.

The same evidence also generates a prompt-safe content brief. The brief turns detected gaps into recommended sections, schema guidance, trust guidance, citation guidance, and a writer prompt that explicitly avoids invented rankings, traffic, reviews, prices, credentials, citations, or private analytics data.

The audit API also accepts `{ "demo": true }` and returns a built-in sample audit. This keeps the demo and export workflow available even when the user has no website URL, no Google account, or no network access to a target site.

The frontend can export the current audit from browser state as Markdown, a standalone writer brief, or JSON. These exports are client-side only and do not write reports to disk or the Flask server.

The browser also keeps a small recent audit history in `localStorage`. It stores the latest URL scans only in the current browser so a user can reopen a report after a refresh or after scanning another site. It is capped, clearable from the UI, and does not create server-side report storage.

Growth reports can also be saved in browser `localStorage`. This covers imported CSV, sample growth, and live Google reports so a user can recover the latest growth dashboard without reconnecting or re-importing immediately. It is capped, clearable from the UI, and does not create server-side report storage.

### Setup Assistant Mode

The user sees a one-place Google launcher plus a sandbox demo of the beginner setup journey. This helps validate the product flow before live Google access exists.

The session API also returns platform readiness checks for OAuth credentials, redirect URI shape, local demo mode, hosted HTTPS mode, Flask secret key, and token storage. The frontend renders those checks in the setup assistant and can copy a safe operator checklist.

### Live Google Mode

The user authorizes Google OAuth. The app lists Search Console and GA4 properties, runs reports, and generates SEO opportunities.

The growth dashboard renders the same metrics that can be exported from browser state as Markdown or JSON: source status, clicks, impressions, CTR, average position, organic sessions, revenue, opportunity queues, top queries, top pages, channels, and landing pages.

### CSV Import Mode

When OAuth is not configured, the user can import exported Search Console and GA4 CSV files in the browser. The frontend parses recognized headers, builds the same growth report shape, and runs the same opportunity UI without uploading files to the Flask server.

Supported Search Console headers include `Query`, `Page`, `Clicks`, `Impressions`, `CTR`, and `Position`. Supported GA4 headers include channel or landing page labels plus `Sessions`, `Total users`, `Engaged sessions`, and page view columns.

CSV import is a local fallback, not a source-of-truth data warehouse. It does not persist files, refresh Google data, or verify access permissions.

The action queue is assembled in the browser from the current audit and growth report. It combines SEO quick wins, GEO quick wins, writer-brief sections, ranking wins, CTR rewrites, and page priorities into one prioritized implementation queue. The same rows power the on-screen priority filters and the CSV or Markdown exports.

### Hosted Discovery Mode

Hosted deployments expose crawl-friendly discovery files for the app itself:

- `/robots.txt` allows the public app shell and points crawlers to `/sitemap.xml`.
- `/sitemap.xml` lists the app shell plus discovery files using the configured `APP_BASE_URL` or detected platform URL.
- `/llms.txt` summarizes the project, capabilities, and limitations for agent-style readers.
- `/privacy` and `/terms` provide public trust pages for users and OAuth reviewers.

API and OAuth routes are disallowed in `robots.txt` because they are interactive endpoints, not useful public content pages.

The homepage also exposes share and structured metadata:

- canonical URL
- Open Graph title, description, URL, and image
- Twitter summary card metadata
- Schema.org `SoftwareApplication` JSON-LD with free/open-source positioning and feature list

## Token Storage

The starter uses `FileTokenStore` under `instance/oauth_tokens` for local development. This path is ignored by Git.

When `TOKEN_ENCRYPTION_KEY` is set, token payloads are encrypted before they are written to disk. This is a hosted-trial improvement, not a complete SaaS identity system.

For hosted multi-user deployments, replace it with encrypted database-backed storage.
