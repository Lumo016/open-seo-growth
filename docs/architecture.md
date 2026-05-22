# Architecture

Open SEO Growth is intentionally small:

- Flask serves the app, routes, and JSON APIs.
- The frontend is a single HTML/CSS/JS workbench.
- Google API calls are isolated in `seo_growth/analytics.py`.
- OAuth handling is isolated in `seo_growth/google_oauth.py`.
- URL-only audit logic is isolated in `seo_growth/instant_audit.py`.
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

The user enters a URL and receives an instant technical/on-page audit. This mode does not require OAuth, GA4, or Search Console.

### Setup Assistant Mode

The user sees a one-place Google launcher plus a sandbox demo of the beginner setup journey. This helps validate the product flow before live Google access exists.

### Live Google Mode

The user authorizes Google OAuth. The app lists Search Console and GA4 properties, runs reports, and generates SEO opportunities.

## Token Storage

The starter uses `FileTokenStore` under `instance/oauth_tokens` for local development. This path is ignored by Git.

For hosted multi-user deployments, replace it with encrypted database-backed storage.
