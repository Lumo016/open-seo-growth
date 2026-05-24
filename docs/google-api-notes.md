# Google API Notes

This project uses three Google APIs.

## Search Console

The OAuth scope is:

```text
https://www.googleapis.com/auth/webmasters.readonly
```

Endpoints:

- `GET https://searchconsole.googleapis.com/webmasters/v3/sites`
- `POST https://searchconsole.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query`

The first endpoint discovers verified site properties. The second endpoint reads clicks, impressions, CTR, and position.

## GA4 Admin

The OAuth scope is:

```text
https://www.googleapis.com/auth/analytics.readonly
```

Endpoint:

```text
GET https://analyticsadmin.googleapis.com/v1beta/accountSummaries
```

The code falls back to `v1alpha` if `v1beta` is unavailable.

## GA4 Data

Endpoint:

```text
POST https://analyticsdata.googleapis.com/v1beta/properties/{propertyId}:runReport
```

Reports used:

- summary metrics
- channel groups
- landing pages
- events
- ecommerce purchases and purchase revenue

## OAuth Trust Pages

Public OAuth deployments should expose user-facing trust pages before asking real users to authorize Google access:

- `/privacy`
- `/terms`

The starter pages explain read-only Google data access, storage limits, exports, token handling, and acceptable use. Hosted operators should adapt them to their own company, jurisdiction, processors, support process, and user data deletion path.
