# Deployment Notes

Open SEO Growth can run anywhere a small Flask app can run.

## Free-Tier-Friendly Shape

The project is designed to stay small enough for free or hobby hosting experiments:

- one Flask web process
- no required background worker
- no required database for local demos
- a built-in sample audit and sample growth report
- a `/healthz` endpoint for platform health checks
- in-process anonymous audit rate limiting
- Docker support for hosts that accept a container

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

## Minimum Production Checklist

- Set a strong `FLASK_SECRET_KEY`.
- Use HTTPS.
- Remove `ALLOW_INSECURE_OAUTH=1`.
- Set `APP_BASE_URL` to the public domain.
- Set `GOOGLE_REDIRECT_URI` to `https://your-domain.com/auth/google/callback`.
- Add that redirect URI to the Google Cloud OAuth client.
- Replace file-based token storage before hosting multiple users.
- Keep `AUDIT_RATE_LIMIT_PER_HOUR` above zero before allowing anonymous public audits.
- Keep network egress controls on the host, even though the app blocks private URL targets.

The setup assistant exposes the same checklist in the UI and lets operators copy a safe Markdown version without client secrets or OAuth tokens.

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
