# Render Deployment

This repository includes `render.yaml` for a low-friction Render trial deployment.

The Blueprint creates one Docker web service with:

- `runtime: docker`
- `plan: free`
- `healthCheckPath: /healthz`
- generated `FLASK_SECRET_KEY`
- generated `TOKEN_ENCRYPTION_KEY`
- automatic `RENDER_EXTERNAL_URL` detection for the public app URL
- public audit rate limiting enabled
- no database requirement for the sample audit, URL audit, CSV import, setup assistant, or sample growth report

## Deploy Flow

1. Push this repository to GitHub.
2. Open Render and create a new Blueprint from the repository.
3. Confirm the service settings from `render.yaml`.
4. Deploy the service.
5. Open the generated Render URL and test:
   - `GET /healthz`
   - `Load sample audit`
   - `Load sample CSV`
   - `Load sample growth`
   - `Run instant audit` with a public website URL

## Update The Public URL

Render provides `RENDER_EXTERNAL_URL` after the service is created. Open SEO Growth uses it as the public base URL when `APP_BASE_URL` is not set.

```env
APP_BASE_URL=
RENDER_EXTERNAL_URL=https://your-render-service.onrender.com
GOOGLE_REDIRECT_URI=
```

With that setup, the app exposes the redirect URI as:

```text
https://your-render-service.onrender.com/auth/google/callback
```

If you add a custom domain, set `APP_BASE_URL` to the final HTTPS origin. `GOOGLE_REDIRECT_URI` can usually stay empty because it defaults to `{APP_BASE_URL}/auth/google/callback`.

## Add Google Later

The first deployment works without Google OAuth. When you are ready to test live Search Console and GA4 data, add these environment variables in Render:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
```

Then copy the redirect URI shown in the setup assistant and add it to the Google Cloud OAuth client.

## Important Limits

Render's default filesystem is ephemeral. The starter `FileTokenStore` can encrypt token files when `TOKEN_ENCRYPTION_KEY` is set, but files can still disappear across deploys or restarts. A public multi-user product should replace it with encrypted database-backed token storage.

The built-in rate limiter is in-memory. It is useful for a single-process trial, but a larger public deployment should add platform-level or edge rate limiting.
