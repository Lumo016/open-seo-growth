# CSV Import

CSV import is the no-OAuth data path for users who can export Google data but cannot connect Google directly yet.

The browser parses selected files locally and builds the same growth dashboard shape used by the live Google report. CSV files are not uploaded to the Flask server, saved to disk, or committed by the app.

## Supported Search Console Files

The importer accepts exported query or page rows with these headers:

- `Query` or `Page`
- `Clicks`
- `Impressions`
- `CTR`
- `Position`

`CTR` can be a percentage such as `1.23%` or a decimal such as `0.0123`.

The imported Search Console rows power:

- clicks, impressions, average CTR, and weighted average position
- low-hanging ranking wins
- CTR rewrite candidates
- page priority opportunities
- ranking distribution
- top query and top page tables
- growth report and action queue exports

## Supported GA4 Files

The importer accepts GA4 channel rows with:

- `Session default channel group`
- `Sessions`
- `Total users`
- `Engaged sessions`

The importer accepts GA4 landing page rows with:

- `Landing page + query string`
- `Sessions`
- `Screen page views`
- `Engaged sessions`

GA4 CSV rows power:

- organic sessions
- traffic source mix
- channel table
- landing page table

## Limits

CSV import is a fallback path. It does not refresh data, prove permissions, include prior-period trends, or replace OAuth for ongoing hosted SaaS use.

Use OAuth when the deployment is ready and the user can authorize read-only access. Use CSV import when the user has exports but cannot complete OAuth setup.
