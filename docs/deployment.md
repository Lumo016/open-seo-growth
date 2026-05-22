# Deployment Notes

Open SEO Growth can run anywhere a small Flask app can run.

## Minimum Production Checklist

- Set a strong `FLASK_SECRET_KEY`.
- Use HTTPS.
- Remove `ALLOW_INSECURE_OAUTH=1`.
- Set `APP_BASE_URL` to the public domain.
- Set `GOOGLE_REDIRECT_URI` to `https://your-domain.com/auth/google/callback`.
- Add that redirect URI to the Google Cloud OAuth client.
- Replace file-based token storage before hosting multiple users.

## Hosted SaaS Mode

In hosted SaaS mode, the platform owner configures one Google OAuth client. End users should only see a consent screen and property selection.

Recommended additions:

- user accounts
- team/workspace membership
- encrypted token storage
- account identity display
- report caching
- rate limiting
- audit/report export

## Self-Host Mode

In self-host mode, each deployer creates their own Google Cloud OAuth client and fills `.env`.

This is simplest for private use, demos, and internal consulting workflows.
