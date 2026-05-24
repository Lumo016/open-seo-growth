# Beginner Google Setup Flow

This document describes the intended no-expertise user journey.

## If The User Has No GA4 Or Search Console

Do not stop the session. Start with `Instant audit`.

The user should see:

1. whether the site responds
2. whether the page has basic indexable content
3. whether robots/sitemap signals exist
4. whether analytics tags are detectable
5. the exact next setup steps

## One-Click Launcher Model

The product should feel one-click even though Google still requires login,
consent, site ownership verification, and tag installation.

The launcher should give beginners one place to:

1. authorize Google when platform OAuth is configured
2. open Search Console to add and verify the site
3. open GA4 to create a property and web stream
4. open Tag Manager when the site needs a container-based install
5. open website-builder installation help
6. return and re-check available Google properties

The app also generates a beginner setup plan that can be copied or downloaded.
That plan should include:

1. the website value the user should paste into Google tools
2. the current Open SEO Growth OAuth status
3. whether the audited page already appears to have a GA4 or GTM tag
4. the official Search Console, GA4, Tag Manager, and website-builder links
5. a safety note not to share passwords, client secrets, OAuth tokens, or private analytics exports

The app cannot safely create or verify a Google account, Search Console
property, or GA4 installation without the user's Google login and ownership
proof. The commercial UX goal is to remove guessing, not bypass Google's
security model.

## If The User Has A Google Account

The hosted app should provide one `Connect Google` button. After OAuth:

1. call Search Console `sites.list`
2. call GA4 Admin `accountSummaries.list`
3. show available properties
4. explain empty states plainly

## Empty State Copy

No Search Console sites:

```text
No verified Search Console sites were found for this Google account. Verify site ownership in Search Console, then refresh.
```

No GA4 properties:

```text
No GA4 properties were found for this Google account. Create or install GA4 for this site, then refresh.
```

## Future Automation

Later versions can add guided installers for:

- Shopify
- WordPress
- Webflow
- Wix
- custom HTML

The app can generate meta tag, DNS, or HTML-file instructions, but the user or website platform still needs to place the verification signal.
