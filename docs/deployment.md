# Deployment Notes

Open SEO Growth can run anywhere a small Flask app can run.

## Free-Tier-Friendly Shape

The project is designed to stay small enough for free or hobby hosting experiments:

- one Flask web process
- no required background worker
- no required database for local demos
- a built-in sample audit and sample growth report
- a `/healthz` endpoint for platform health checks
- hosted discovery files at `/robots.txt`, `/sitemap.xml`, and `/llms.txt`
- in-process anonymous audit rate limiting
- Docker support for hosts that accept a container
- a `render.yaml` Blueprint for a one-service Render trial

This does not mean every public host is production-ready for OAuth and customer data. Use the platform readiness checklist in the app before asking real users to connect Google.

## Docker

Build and run locally:

```bash
docker build -t open-seo-growth .
docker run --rm -p 8792:8792 --env-file .env open-seo-growth
```

Health check:

```text
GET /healthz
```

The container starts the Flask app through Waitress and reads `PORT` from the environment. For a public domain, set:

```env
APP_BASE_URL=https://your-domain.com
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback
ALLOW_INSECURE_OAUTH=
AUDIT_RATE_LIMIT_PER_HOUR=30
```

## Render Blueprint

`render.yaml` defines a single Docker web service with `/healthz` as the health check path. It generates `FLASK_SECRET_KEY`, keeps anonymous audit rate limiting enabled, and avoids hardcoding Google OAuth client secrets.

The Blueprint starts in No-Google mode so a fresh deployment can still run the sample audit, live public URL audit, setup assistant, and sample growth report. The app uses Render's `RENDER_EXTERNAL_URL` as its public base URL when `APP_BASE_URL` is empty. Add Google OAuth environment variables later when the final HTTPS domain is known.

See [render-deployment.md](render-deployment.md).

## Minimum Production Checklist

- Set a strong `FLASK_SECRET_KEY`.
- Use HTTPS.
- Remove `ALLOW_INSECURE_OAUTH=1`.
- Set `APP_BASE_URL` to the public domain, unless the host provides `RENDER_EXTERNAL_URL`.
- Set `GOOGLE_REDIRECT_URI` to `https://your-domain.com/auth/google/callback`, or leave it empty so it follows `APP_BASE_URL`.
- Add that redirect URI to the Google Cloud OAuth client.
- Replace file-based token storage before hosting multiple users.
- Keep `AUDIT_RATE_LIMIT_PER_HOUR` above zero before allowing anonymous public audits.
- Keep network egress controls on the host, even though the app blocks private URL targets.
- Confirm `/robots.txt`, `/sitemap.xml`, `/llms.txt`, and `/healthz` return the expected public origin.

The setup assistant exposes the same checklist in the UI and lets operators copy a safe Markdown version without client secrets or OAuth tokens.

## Hosted Discovery Files

The app generates discovery files from the configured public origin:

- `GET /robots.txt`
- `GET /sitemap.xml`
- `GET /llms.txt`

These routes help a public deployment describe itself as an SEO/GEO workbench. They do not expose OAuth tokens, analytics data, customer reports, or private audit results.

## Hosted SaaS Mode

In hosted SaaS mode, the platform owner configures one Google OAuth client. End users should only see a consent screen and property selection.

Recommended additions:

- user accounts
- team/workspace membership
- encrypted token storage
- account identity display
- report caching
- durable cross-instance rate limiting
- audit/report export
- billing or usage limits if public scanning becomes expensive

## Self-Host Mode

In self-host mode, each deployer creates their own Google Cloud OAuth client and fills `.env`.

This is simplest for private use, demos, and internal consulting workflows.

## Public URL Audit Safety

The URL audit is intended for normal public websites. Before fetching a submitted URL, the app rejects:

- non-HTTP(S) schemes
- localhost and private network targets
- embedded username/password credentials
- non-standard ports outside 80 and 443

Redirect destinations are checked with the same rules. This reduces SSRF risk for a public scanner, but it is not a substitute for host-level egress policy, abuse monitoring, and rate limits.

## Audit Rate Limiting

The starter includes an in-memory per-client limit for live URL audits. It is controlled by:

```env
AUDIT_RATE_LIMIT_PER_HOUR=30
```

Sample audit and sample growth reports are not counted because they do not fetch external sites. The built-in limiter is useful for free-tier demos and single-process deployments. If the app runs behind multiple instances, a serverless edge layer, or a CDN, add a platform-level limiter because in-memory counters are not shared across processes.
