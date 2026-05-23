# GEO Readiness

Open SEO Growth treats GEO as a practical readiness layer on top of regular SEO. The app does not promise AI citations, AI Overview inclusion, chatbot rankings, or traffic gains. It checks whether a page has signals that make it easier for search systems and answer engines to understand, summarize, and reference.

## What The Audit Checks

- Substantial visible, crawlable text.
- A clear title and H1 that name the topic, entity, product, or question.
- Structured data that matches visible content.
- Useful entity and content schema types such as `Organization`, `WebSite`, `WebPage`, `Article`, `Product`, `SoftwareApplication`, `FAQPage`, `HowTo`, or `LocalBusiness`.
- Question-led or answer-led sections.
- Trust signals such as author, site name, about, contact, privacy, terms, sources, references, or editorial language.
- External references where claims benefit from citations.
- Search access through noindex checks.
- Optional `/llms.txt` availability.

## Scoring Model

The GEO score is a 100-point heuristic:

```text
15  Crawlable main content is substantial
12  Title and H1 make the page topic explicit
14  Structured data is present
10  Schema includes useful entity or content types
10  Question or answer-oriented sections are detectable
10  Trust, ownership, or source signals are visible
 8  External references or citations exist
 8  Page is not blocked by robots meta
 7  Meta description summarizes the page
 6  Optional llms.txt is reachable
```

Grades:

- `Strong`: 80+
- `Promising`: 60-79
- `Needs structure`: below 60

## Notes For Contributors

Keep this feature transparent. If a check is speculative, label it as optional or experimental in the product UI and API response. Do not imply that any single file, tag, or schema type guarantees inclusion in AI answer products.

Current implementation limits:

- Content freshness signals are not scored yet.
- Author and organization pages are not crawled deeply.
- JSON-LD is detected, but not fully validated against visible page content.
- Page-type-specific scoring profiles are not implemented yet.

## Exported Reports

The browser UI can export the current audit as Markdown or JSON. Markdown is meant for client handoff and includes the SEO score, GEO score, priority fixes, checklists, evidence, and setup limits. JSON is meant for debugging, automation, or downstream integrations.

No export is written to the server by default.

Use the built-in sample audit to test exports without fetching a real website.

## Reference Points

- Google Search Central: [Create helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- Google Search Central: [Intro to structured data markup](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data)
- Schema.org: [Schemas](https://schema.org/docs/schemas.html)
- llms.txt proposal: [llmstxt.org](https://llmstxt.org/)
