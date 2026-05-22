# Security Policy

## Supported Versions

Open SEO Growth is an early open-source starter. Security fixes should target the `main` branch.

## Reporting A Vulnerability

Please do not open a public issue for secrets, OAuth flaws, or private data exposure.

Instead, create a private GitHub security advisory if available, or contact the repository owner through GitHub.

## Sensitive Data

The project should not store real OAuth tokens, analytics exports, or customer reports in Git.

Ignored runtime paths:

- `.env`
- `.env.*`
- `instance/`
- `*.log`

For public multi-user hosting, replace the local file token store with encrypted database-backed storage before serving real users.
