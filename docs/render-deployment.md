# Render Deployment

This repository includes `render.yaml` for a low-friction Render trial deployment.

The Blueprint creates one Docker web service with:

- `runtime: docker`
- `plan: free`
- `healthCheckPath: /healthz`
- generated `FLASK_SECRET_KEY`
- public audit rate limiting enabled
- no database requirement for the sample audit, URL audit, setup assistant, or sample growth report

## Deploy Flow

1. Push this repository to GitHub.
2. Open Render and create a new Blueprint from the repository.
3. Confirm the service settings from `render.yaml`.
4. Deploy the service.
5. Open the generated Render URL and test:
   - `GET /healthz`
   - `Load sample audit`
   - `Load sample growth`
   - `Run instant audit` with a public website URL

## Update The Public URL

The starter Blueprint sets:

```env
APP_BASE_URL=https://open-seo-growth.onrender.com
GOOGLE_REDIRECT_URI=https://open-seo-growth.onrender.com/auth/google/callback
```

If Render assigns a different service URL, or if you add a custom domain, update both environment variables to the final HTTPS origin.

## Add Google Later

The first deployment works without Google OAuth. When you are ready to test live Search Console and GA4 data, add these environment variables in Render:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://your-render-or-custom-domain/auth/google/callback
```

Then add the same redirect URI to the Google Cloud OAuth client.

## Important Limits

Render's default filesystem is ephemeral. The starter `FileTokenStore` is acceptable for demo and private single-user trials, but tokens can disappear across deploys or restarts. A public multi-user product should replace it with encrypted database-backed token storage.

The built-in rate limiter is in-memory. It is useful for a single-process trial, but a larger public deployment should add platform-level or edge rate limiting.
