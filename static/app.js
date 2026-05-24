const $ = (id) => document.getElementById(id);

const state = {
  session: null,
  connections: null,
  audit: null,
  report: null,
  activeView: "auditView",
  simulatorStep: 0,
};

function showToast(message, type = "") {
  const el = $("toast");
  el.textContent = message;
  el.className = `toast show ${type}`;
  window.setTimeout(() => {
    el.className = "toast";
  }, 4200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function compactNumber(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return "-";
  return Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(num);
}

function percent(value, digits = 1) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return "-";
  return `${(num * 100).toFixed(digits)}%`;
}

function currency(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num) || num === 0) return "-";
  return Intl.NumberFormat("en", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(num);
}

function milliseconds(value) {
  if (value === null || value === undefined || value === "") return "-";
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return `${Math.round(num).toLocaleString()} ms`;
}

function kilobytes(value) {
  if (value === null || value === undefined || value === "") return "-";
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return `${num.toLocaleString(undefined, { maximumFractionDigits: 1 })} KB`;
}

function robotsAccessLabel(access) {
  if (access?.allowed === true) return access.checked ? "Allowed" : "Assumed allowed";
  if (access?.allowed === false) return "Blocked";
  return access?.status || "Not checked";
}

function robotsAccessNote(access) {
  return access?.reason || "Exact URL permission was not checked.";
}

function canonicalLabel(status) {
  if (status?.status) return status.status;
  if (status?.declared === false) return "Missing";
  return "Not checked";
}

function canonicalNote(status) {
  return status?.reason || "Canonical target was not checked.";
}

function sitemapCoverageLabel(coverage) {
  if (coverage?.status) return coverage.status;
  if (coverage?.included === true) return "Listed";
  if (coverage?.included === false) return "Not listed";
  return "Not checked";
}

function sitemapCoverageNote(coverage) {
  return coverage?.reason || "Sitemap coverage was not checked.";
}

function xRobotsLabel(status) {
  return status?.status || "Not checked";
}

function xRobotsNote(status) {
  return status?.reason || "X-Robots-Tag header was not checked.";
}

function jsonLdLabel(summary) {
  const scriptCount = Number(summary?.json_ld_scripts || 0);
  const errors = summary?.json_ld_parse_errors || [];
  if (errors.length) return "Parse errors";
  if (scriptCount > 0) return "Valid";
  return "Not detected";
}

function jsonLdNote(summary) {
  const scriptCount = Number(summary?.json_ld_scripts || 0);
  const validCount = Number(summary?.json_ld_valid_scripts || 0);
  const errors = summary?.json_ld_parse_errors || [];
  if (errors.length) return `${errors.length} JSON-LD script${errors.length === 1 ? "" : "s"} failed to parse.`;
  if (scriptCount > 0) return `${validCount} of ${scriptCount} JSON-LD scripts parsed.`;
  return "No JSON-LD script was detected.";
}

function isoDate() {
  return new Date().toISOString().slice(0, 10);
}

function trendLabel(value, inverted = false) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  const improved = inverted ? num > 0 : num >= 0;
  return `${improved ? "+" : ""}${num.toFixed(1)}% vs prior period`;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.message || payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function option(value, label) {
  return `<option value="${escapeHtml(value)}">${escapeHtml(label || value)}</option>`;
}

function fileSlug(value) {
  try {
    const url = new URL(value);
    return url.hostname.replace(/^www\./, "").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();
  } catch {
    return "seo-geo-audit";
  }
}

function markdownList(items, emptyText) {
  const values = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!values.length) return `- ${emptyText}`;
  return values.map((item) => `- ${item}`).join("\n");
}

function markdownChecks(checks) {
  const values = Array.isArray(checks) ? checks : [];
  if (!values.length) return "- No checks available.";
  return values.map((check) => {
    const status = check.ok ? "Pass" : check.experimental ? "Optional" : "Fix";
    const note = check.ok ? `${check.weight} points` : check.fix;
    return `- ${status}: ${check.label} - ${note}`;
  }).join("\n");
}

function markdownWins(items, emptyText) {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) return `- ${emptyText}`;
  return values.map((item) => `- ${item.impact || "Medium"}: ${item.title || "Opportunity"} - ${item.action || "Review this item."}`).join("\n");
}

function markdownBriefRows(items, emptyText) {
  const values = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!values.length) return `- ${emptyText}`;
  return values.map((item) => {
    if (typeof item === "string") return `- ${item}`;
    return `- ${item.priority || "Medium"}: ${item.title || "Recommendation"} - ${item.reason || "Review this item."}`;
  }).join("\n");
}

function contentBriefLines(audit) {
  const brief = audit?.geo_report?.content_brief || {};
  if (!brief.title) return ["No GEO content brief generated."];
  return [
    `Primary topic: ${brief.primary_topic || "-"}`,
    `Page type: ${brief.page_type || "-"}`,
    `Audience: ${brief.audience || "-"}`,
    ``,
    `### Recommended Sections`,
    ``,
    markdownBriefRows(brief.recommended_sections, "No section recommendations generated."),
    ``,
    `### Schema Recommendations`,
    ``,
    markdownBriefRows(brief.schema_recommendations, "No schema recommendations generated."),
    ``,
    `### Trust Recommendations`,
    ``,
    markdownBriefRows(brief.trust_recommendations, "No trust recommendations generated."),
    ``,
    `### Citation Recommendations`,
    ``,
    markdownBriefRows(brief.citation_recommendations, "No citation recommendations generated."),
    ``,
    `### Safe Writer Prompt`,
    ``,
    brief.safe_prompt || "No prompt generated.",
    ``,
    `### Handoff Notes`,
    ``,
    markdownBriefRows(brief.handoff_notes, "Use this as editorial guidance, not a ranking promise."),
  ];
}

function buildBriefMarkdown(audit) {
  return [
    `# GEO Content Brief`,
    ``,
    `Audited URL: ${audit?.audited_url || "-"}`,
    `Generated: ${isoDate()}`,
    audit?.demo ? `Mode: Built-in sample audit` : `Mode: Live URL audit`,
    ``,
    ...contentBriefLines(audit),
    ``,
    `---`,
    `Generated by Open SEO Growth. Use this brief as editorial guidance, not as a ranking guarantee.`,
  ].join("\n");
}

function markdownOpportunityRows(rows, titleKey, emptyText) {
  const values = Array.isArray(rows) ? rows : [];
  if (!values.length) return `- ${emptyText}`;
  return values.slice(0, 10).map((row, index) => {
    const title = row[titleKey] || row.label || "-";
    return `${index + 1}. ${title} - ${opportunityMeta(row)} | Score ${row.opportunity_score ?? "-"}`;
  }).join("\n");
}

function markdownDataRows(rows, mapper, emptyText) {
  const values = Array.isArray(rows) ? rows : [];
  if (!values.length) return `- ${emptyText}`;
  return values.slice(0, 10).map((row, index) => {
    const item = mapper(row);
    return `${index + 1}. ${item.title} - ${item.meta}`;
  }).join("\n");
}

function sourceStatusText(report, key) {
  const status = report?.scorecard?.source_status || {};
  const diagnosis = report?.scorecard?.diagnosis || {};
  const labels = {
    gsc: status.gsc ? "Connected with search demand" : "Waiting for Search Console data",
    ga4: status.ga4 ? "Connected with traffic data" : "Waiting for GA4 traffic",
    ecommerce: status.ecommerce ? "Revenue data available" : "Revenue not connected",
  };
  const diagnosisKeys = {
    gsc: "visibility_label",
    ga4: "traffic_label",
    ecommerce: "revenue_label",
  };
  return diagnosis[diagnosisKeys[key]] || labels[key] || "Unknown";
}

function growthReportSlug(report) {
  const target = report?.target_scope?.url || report?.gsc?.site_url || "growth-report";
  return `${fileSlug(target)}-growth-report`;
}

function buildGrowthReportMarkdown(report) {
  const gsc = report.gsc || {};
  const ga4 = report.ga4 || {};
  const summary = gsc.summary || {};
  const trends = gsc.trends || {};
  const score = report.scorecard || {};
  const metrics = score.metrics || {};
  const opp = report.opportunities || {};
  return [
    `# SEO Growth Report`,
    ``,
    `Generated: ${report.generated_at || new Date().toISOString()}`,
    report.demo ? `Mode: Built-in sample growth report` : `Mode: Live Google data report`,
    `Target: ${report.target_scope?.url || report.target_scope?.label || gsc.site_url || "-"}`,
    `Period: ${score.period_label || `${report.period?.start_date || "-"} to ${report.period?.end_date || "-"}`}`,
    ``,
    `## Measurement Status`,
    ``,
    `- Search Console: ${sourceStatusText(report, "gsc")}`,
    `- GA4 traffic: ${sourceStatusText(report, "ga4")}`,
    `- Ecommerce: ${sourceStatusText(report, "ecommerce")}`,
    ``,
    `## Scorecard`,
    ``,
    `- Clicks: ${compactNumber(summary.clicks)} (${trendLabel(trends.clicks) || "no prior-period comparison"})`,
    `- Impressions: ${compactNumber(summary.impressions)} (${trendLabel(trends.impressions) || "no prior-period comparison"})`,
    `- Average CTR: ${percent(summary.ctr)} (${trendLabel(trends.ctr) || "no prior-period comparison"})`,
    `- Average position: ${summary.position ? Number(summary.position).toFixed(1) : "-"} (${trendLabel(trends.position, true) || "no prior-period comparison"})`,
    `- Organic sessions: ${compactNumber(metrics.organic_sessions)}`,
    `- Revenue: ${currency(metrics.revenue)}`,
    ``,
    `## Low-Hanging Ranking Wins`,
    ``,
    markdownOpportunityRows(opp.low_hanging_queries, "query", "No ranking wins found."),
    ``,
    `## CTR Rewrite Queue`,
    ``,
    markdownOpportunityRows(opp.ctr_opportunities, "query", "No CTR rewrite candidates found."),
    ``,
    `## Page Priority Queue`,
    ``,
    markdownOpportunityRows(opp.page_opportunities, "page", "No page-level opportunities found."),
    ``,
    `## Ranking Distribution`,
    ``,
    markdownDataRows(opp.rank_buckets, (row) => ({
      title: row.label || "-",
      meta: `${compactNumber(row.query_count)} queries | ${compactNumber(row.impressions)} impressions | ${percent(row.share, 0)} of demand`,
    }), "No ranking distribution available."),
    ``,
    `## Top Queries`,
    ``,
    markdownDataRows(gsc.top_queries, (row) => ({
      title: row.query || "-",
      meta: `${compactNumber(row.clicks)} clicks | ${compactNumber(row.impressions)} impressions | CTR ${percent(row.ctr)} | Pos ${Number(row.position || 0).toFixed(1)}`,
    }), "No query rows available."),
    ``,
    `## Top Search Pages`,
    ``,
    markdownDataRows(gsc.top_pages, (row) => ({
      title: row.page || "-",
      meta: `${compactNumber(row.clicks)} clicks | ${compactNumber(row.impressions)} impressions | CTR ${percent(row.ctr)} | Pos ${Number(row.position || 0).toFixed(1)}`,
    }), "No page rows available."),
    ``,
    `## GA4 Channels`,
    ``,
    markdownDataRows(ga4.channel_groups, (row) => ({
      title: channelName(row),
      meta: `${compactNumber(rowMetric(row, "sessions"))} sessions | ${compactNumber(rowMetric(row, "totalUsers"))} users | ${compactNumber(rowMetric(row, "engagedSessions"))} engaged sessions`,
    }), "No GA4 channel rows available."),
    ``,
    `## Landing Pages`,
    ``,
    markdownDataRows(ga4.landing_pages, (row) => ({
      title: row.dimensions?.landingPagePlusQueryString || row.dimensions?.landingPage || "-",
      meta: `${compactNumber(rowMetric(row, "sessions"))} sessions | ${compactNumber(rowMetric(row, "screenPageViews"))} views | ${compactNumber(rowMetric(row, "engagedSessions"))} engaged sessions`,
    }), "No landing page rows available."),
    ``,
    `---`,
    `Generated by Open SEO Growth. Opportunity scoring uses Search Console impressions, average position, and heuristic CTR gaps.`,
  ].join("\n");
}

function priorityRank(priority) {
  const value = String(priority || "").toLowerCase();
  if (value === "high") return 3;
  if (value === "medium") return 2;
  if (value === "low") return 1;
  return 0;
}

function priorityFromScore(score) {
  const value = Number(score || 0);
  if (value >= 250) return "High";
  if (value >= 80) return "Medium";
  return "Low";
}

function effortFromPriority(priority) {
  return priority === "High" ? "Medium" : priority === "Medium" ? "Low" : "Low";
}

function buildActionRows() {
  const rows = [];
  const audit = state.audit || null;
  const report = state.report || null;
  if (audit) {
    const auditUrl = audit.audited_url || "-";
    (audit.quick_wins || []).forEach((item) => {
      rows.push({
        source: "Audit",
        type: "SEO readiness",
        priority: item.impact || "Medium",
        title: item.title || "SEO fix",
        action: item.action || "Review this SEO issue.",
        evidence: `SEO ${audit.score ?? "-"} (${audit.grade || "Not graded"}) | ${auditUrl}`,
        effort: effortFromPriority(item.impact),
        status: "Open",
      });
    });
    const geo = audit.geo_report || {};
    (geo.quick_wins || []).forEach((item) => {
      rows.push({
        source: "GEO",
        type: "AI answer readiness",
        priority: item.impact || "Medium",
        title: item.title || "GEO fix",
        action: item.action || "Review this GEO issue.",
        evidence: `GEO ${geo.score ?? "-"} (${geo.grade || "Not graded"}) | ${auditUrl}`,
        effort: effortFromPriority(item.impact),
        status: "Open",
      });
    });
    const brief = geo.content_brief || {};
    (brief.recommended_sections || []).forEach((item) => {
      rows.push({
        source: "GEO brief",
        type: "Writer handoff",
        priority: item.priority || "Medium",
        title: item.title || "Content section",
        action: item.reason || "Use the content brief to improve this page.",
        evidence: brief.primary_topic || auditUrl,
        effort: "Medium",
        status: "Open",
      });
    });
  }
  if (report) {
    const opp = report.opportunities || {};
    (opp.low_hanging_queries || []).forEach((row) => {
      const priority = priorityFromScore(row.opportunity_score);
      rows.push({
        source: "Search Console",
        type: "Ranking win",
        priority,
        title: row.query || "Query opportunity",
        action: "Improve the ranking page with clearer intent coverage, internal links, and supporting sections.",
        evidence: opportunityMeta(row),
        effort: effortFromPriority(priority),
        status: "Open",
      });
    });
    (opp.ctr_opportunities || []).forEach((row) => {
      const priority = row.missed_clicks >= 20 ? "High" : row.missed_clicks >= 5 ? "Medium" : "Low";
      rows.push({
        source: "Search Console",
        type: "CTR rewrite",
        priority,
        title: row.query || "CTR opportunity",
        action: "Rewrite title, meta description, H1, and page intro to better match the visible query intent.",
        evidence: opportunityMeta(row),
        effort: "Low",
        status: "Open",
      });
    });
    (opp.page_opportunities || []).forEach((row) => {
      const priority = priorityFromScore(row.opportunity_score);
      rows.push({
        source: "Search Console",
        type: "Page priority",
        priority,
        title: row.page || "Page opportunity",
        action: "Refresh this page, strengthen internal links, and align headings with queries that already have impressions.",
        evidence: opportunityMeta(row),
        effort: "Medium",
        status: "Open",
      });
    });
  }
  return rows.sort((a, b) => priorityRank(b.priority) - priorityRank(a.priority));
}

function actionQueueSlug() {
  const target = state.audit?.audited_url || state.report?.target_scope?.url || state.report?.gsc?.site_url || "open-seo-growth";
  return `${fileSlug(target)}-action-queue`;
}

function csvEscape(value) {
  const text = String(value ?? "").replace(/\r?\n/g, " ");
  return /[",]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function buildActionQueueCsv() {
  const headers = ["Source", "Type", "Priority", "Title", "Recommended action", "Evidence", "Effort", "Status"];
  const rows = buildActionRows().map((row) => [
    row.source,
    row.type,
    row.priority,
    row.title,
    row.action,
    row.evidence,
    row.effort,
    row.status,
  ]);
  return [headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");
}

function buildActionQueueMarkdown() {
  const rows = buildActionRows();
  return [
    `# Open SEO Growth Action Queue`,
    ``,
    `Generated: ${new Date().toISOString()}`,
    `Audit URL: ${state.audit?.audited_url || "-"}`,
    `Growth target: ${state.report?.target_scope?.url || state.report?.target_scope?.label || "-"}`,
    ``,
    rows.length ? rows.map((row, index) => [
      `## ${index + 1}. ${row.title}`,
      ``,
      `- Source: ${row.source}`,
      `- Type: ${row.type}`,
      `- Priority: ${row.priority}`,
      `- Effort: ${row.effort}`,
      `- Status: ${row.status}`,
      `- Evidence: ${row.evidence}`,
      `- Recommended action: ${row.action}`,
    ].join("\n")).join("\n\n") : "No open actions yet. Run an audit or growth report first.",
  ].join("\n");
}

function setActionExportReady() {
  const rows = buildActionRows();
  const isReady = rows.length > 0;
  ["copyActionQueueBtn", "downloadActionCsvBtn", "downloadActionMarkdownBtn"].forEach((id) => {
    const button = $(id);
    if (button) button.disabled = !isReady;
  });
  if ($("actionExportSummary")) {
    $("actionExportSummary").textContent = isReady
      ? `${rows.length} open actions ready for CSV or Markdown export.`
      : "Run an audit or growth report to unlock a prioritized work queue for clients, writers, and implementers.";
  }
}

function buildAuditMarkdown(audit) {
  const summary = audit.summary || {};
  const geo = audit.geo_report || {};
  const geoSignals = geo.signals || {};
  const noGoogle = audit.no_google_report || {};
  const starterOffer = noGoogle.starter_offer || {};
  return [
    `# SEO and GEO Audit Report`,
    ``,
    `Audited URL: ${audit.audited_url || "-"}`,
    `Generated: ${isoDate()}`,
    audit.demo ? `Mode: Built-in sample audit` : `Mode: Live URL audit`,
    ``,
    `## Scorecard`,
    ``,
    `- SEO readiness: ${audit.score ?? "-"} (${audit.grade || "Not graded"})`,
    `- GEO readiness: ${geo.score ?? "-"} (${geo.grade || "Not graded"})`,
    `- Google tag: ${summary.ga4_detected || summary.gtm_detected ? "Detected" : "Not detected"}`,
    `- Canonical: ${canonicalLabel(summary.canonical_status)}`,
    `- Robots access: ${robotsAccessLabel(summary.robots_access)}`,
    `- X-Robots-Tag: ${xRobotsLabel(summary.x_robots_tag)}`,
    `- Sitemap coverage: ${sitemapCoverageLabel(summary.sitemap_coverage)}`,
    `- JSON-LD: ${jsonLdLabel(summary)}`,
    `- Initial HTML response: ${milliseconds(summary.response_time_ms)}`,
    `- Initial HTML payload: ${kilobytes(summary.html_kb)}`,
    `- Visible words: ${geoSignals.visible_word_count ?? summary.body_word_count ?? "-"}`,
    `- Schema types: ${(geoSignals.schema_types || summary.schema_types || []).join(", ") || "None detected"}`,
    ``,
    `## Executive Summary`,
    ``,
    `${audit.message || "Instant audit completed."}`,
    ``,
    `${geo.summary || "GEO readiness checks are heuristic and do not guarantee AI answer inclusion or ranking."}`,
    ``,
    `## Priority SEO Fixes`,
    ``,
    markdownWins(audit.quick_wins, "No urgent SEO fixes found."),
    ``,
    `## Priority GEO Fixes`,
    ``,
    markdownWins(geo.quick_wins, "No urgent GEO fixes found."),
    ``,
    `## SEO Checklist`,
    ``,
    markdownChecks(audit.checks),
    ``,
    `## GEO Checklist`,
    ``,
    markdownChecks(geo.checks),
    ``,
    `## Prompt-Safe GEO Content Brief`,
    ``,
    ...contentBriefLines(audit),
    ``,
    `## Evidence`,
    ``,
    `- Title: ${summary.title || "No title found"}`,
    `- Meta description: ${summary.description || "No meta description found"}`,
    `- H1: ${(summary.h1 || []).join(" | ") || "No H1 found"}`,
    `- Canonical: ${summary.canonical || "Not declared"}`,
    `- Canonical target: ${canonicalLabel(summary.canonical_status)} - ${canonicalNote(summary.canonical_status)}`,
    `- Canonical resolved URL: ${summary.canonical_status?.normalized_url || "Not available"}`,
    `- Final URL: ${summary.final_url || audit.audited_url || "-"}`,
    `- Redirected: ${summary.redirected ? "Yes" : "No"}`,
    `- HTTP status: ${audit.status_code || "-"}`,
    `- Content type: ${summary.content_type || "Not detected"}`,
    `- Initial HTML response: ${milliseconds(summary.response_time_ms)}`,
    `- Initial HTML payload: ${kilobytes(summary.html_kb)} (${compactNumber(summary.html_bytes)} bytes)`,
    `- Internal links: ${summary.internal_links ?? 0}`,
    `- External links: ${summary.external_links ?? 0}`,
    `- External reference hosts: ${(summary.external_hosts || []).join(", ") || "None detected"}`,
    `- JSON-LD scripts: ${summary.json_ld_valid_scripts ?? 0} valid / ${summary.json_ld_scripts ?? 0} total`,
    `- JSON-LD parse errors: ${(summary.json_ld_parse_errors || []).join(" | ") || "None detected"}`,
    `- Question headings: ${(summary.question_headings || []).join(" | ") || "None detected"}`,
    `- Published date: ${summary.date_published || geoSignals.date_published || "Not detected"}`,
    `- Updated date: ${summary.date_modified || geoSignals.date_modified || "Not detected"}`,
    `- Robots meta: ${summary.robots_meta || "Not declared"}`,
    `- X-Robots-Tag: ${summary.x_robots_tag?.value || xRobotsLabel(summary.x_robots_tag)} - ${xRobotsNote(summary.x_robots_tag)}`,
    `- robots.txt: ${summary.robots?.ok ? "Reachable" : "Not reachable"}`,
    `- robots.txt URL access: ${robotsAccessLabel(summary.robots_access)} - ${robotsAccessNote(summary.robots_access)}`,
    `- sitemap.xml: ${summary.sitemap?.ok ? "Reachable" : "Not reachable"}`,
    `- sitemap URL coverage: ${sitemapCoverageLabel(summary.sitemap_coverage)} - ${sitemapCoverageNote(summary.sitemap_coverage)}`,
    `- llms.txt: ${summary.llms_txt?.ok ? "Reachable" : "Not reachable or not published"}`,
    ``,
    `## No-Google Handoff`,
    ``,
    markdownList(noGoogle.what_you_can_sell_now, "Use the URL-only audit as the first deliverable."),
    ``,
    `## Starter Offer`,
    ``,
    `Name: ${starterOffer.name || "Starter SEO and GEO cleanup sprint"}`,
    `Audience: ${starterOffer.audience || "Site owners without reliable Google data yet."}`,
    `Timeline: ${starterOffer.timeline || "Audit now; measurement follow-up after Google data accrues."}`,
    ``,
    starterOffer.summary || "Package the URL-only audit into a practical SEO and GEO cleanup proposal.",
    ``,
    markdownList(starterOffer.deliverables, "SEO and GEO scorecard, action plan, and measurement setup handoff."),
    ``,
    `Upgrade trigger: ${starterOffer.upgrade_trigger || "Connect Google later for verified growth reporting."}`,
    ``,
    `## Limits`,
    ``,
    markdownList(noGoogle.limits, "No verified Google performance data is included unless Google is connected."),
    ``,
    `## Next Steps`,
    ``,
    markdownList(audit.next_steps, "Keep monitoring SEO and GEO readiness after content changes."),
    ``,
    `---`,
    `Generated by Open SEO Growth. GEO scoring is a transparent heuristic, not a ranking guarantee.`,
  ].join("\n");
}

function buildStarterOfferMarkdown(audit) {
  const report = audit?.no_google_report || {};
  const offer = report.starter_offer || {};
  return [
    `# ${offer.name || "Starter SEO and GEO cleanup sprint"}`,
    ``,
    `Generated: ${isoDate()}`,
    `Website: ${audit?.audited_url || "-"}`,
    `Audience: ${offer.audience || "Site owners without reliable GA4 or Search Console data yet."}`,
    `Timeline: ${offer.timeline || "Audit now; measurement follow-up after Google data accrues."}`,
    ``,
    `## Proposal Summary`,
    ``,
    offer.summary || "Use the URL-only audit as a practical first SEO and GEO deliverable before Google data exists.",
    ``,
    `## Deliverables`,
    ``,
    markdownList(offer.deliverables || report.what_you_can_sell_now, "SEO and GEO scorecard, action plan, and measurement setup handoff."),
    ``,
    `## Immediate Priorities`,
    ``,
    markdownWins(audit?.quick_wins, "No urgent SEO fixes found in the first scan."),
    ``,
    `## Measurement Upgrade`,
    ``,
    offer.upgrade_trigger || "After GA4 and Search Console collect enough data, run the growth dashboard for verified clicks, impressions, CTR, positions, sessions, pages, and query opportunities.",
    ``,
    `## Limits`,
    ``,
    markdownList(report.limits, "No verified Google performance data is included until Google is connected."),
    ``,
    `---`,
    `Generated by Open SEO Growth.`,
  ].join("\n");
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function setExportReady(isReady) {
  ["copyReportBtn", "downloadMarkdownBtn", "downloadBriefBtn", "downloadJsonBtn"].forEach((id) => {
    const button = $(id);
    if (button) button.disabled = !isReady;
  });
  ["copyStarterOfferBtn", "downloadStarterOfferBtn"].forEach((id) => {
    const button = $(id);
    if (button) button.disabled = !isReady;
  });
  if ($("reportExportSummary")) {
    $("reportExportSummary").textContent = isReady
      ? "Export a client-ready report, a writer brief, or raw JSON evidence from this browser session. No account or Google connection is required."
      : "Run an audit to unlock a Markdown report, writer brief, raw JSON evidence, and a copyable client summary.";
  }
}

function setGrowthExportReady(isReady) {
  ["copyGrowthReportBtn", "downloadGrowthMarkdownBtn", "downloadGrowthJsonBtn"].forEach((id) => {
    const button = $(id);
    if (button) button.disabled = !isReady;
  });
  if ($("growthReportSummary")) {
    $("growthReportSummary").textContent = isReady
      ? "Export the current growth report as Markdown or JSON. The report includes source status, metrics, opportunities, queries, pages, and channels."
      : "Load sample growth or connect Google to unlock a client-ready report with clicks, impressions, CTR, rankings, sessions, and opportunities.";
  }
}

function buildPlatformReadinessMarkdown(session) {
  const readiness = session?.platform_readiness || {};
  const items = Array.isArray(readiness.items) ? readiness.items : [];
  return [
    `# Open SEO Growth Platform Readiness`,
    ``,
    `Generated: ${new Date().toISOString()}`,
    `Mode: ${readiness.mode || "setup_needed"}`,
    `Ready for Google OAuth: ${readiness.ready_for_google ? "Yes" : "No"}`,
    `Hosted SaaS ready: ${readiness.ready_for_hosted_saas ? "Yes" : "No"}`,
    `App base URL: ${readiness.app_base_url || "-"}`,
    `Google redirect URI: ${readiness.redirect_uri || session?.redirect_uri || "-"}`,
    `Token storage: ${readiness.token_store || "file"}`,
    ``,
    `## Checklist`,
    ``,
    items.length ? items.map((item) => {
      const status = item.ok ? "OK" : "Action";
      return `- ${status}: ${item.label} - ${item.status}. ${item.action}`;
    }).join("\n") : "- No readiness checks returned.",
    ``,
    `## Safe Notes`,
    ``,
    `- Do not paste client secrets, OAuth tokens, or private analytics exports into issues.`,
    `- FileTokenStore is for local demos and private single-user trials.`,
    `- Hosted multi-user deployments should use encrypted database-backed token storage.`,
  ].join("\n");
}

function renderPlatformReadiness(session) {
  if (!$("readinessChecklist")) return;
  const readiness = session?.platform_readiness || {};
  const items = Array.isArray(readiness.items) ? readiness.items : [];
  $("readinessSummary").textContent = readiness.summary || "Google connection needs platform setup before users can authorize in one click.";
  $("readinessRedirectUri").textContent = readiness.redirect_uri || session?.redirect_uri || "-";
  $("readinessChecklist").innerHTML = items.length
    ? items.map((item) => `
      <article class="readiness-row ${item.ok ? "ok" : "action"}">
        <span>${item.ok ? "OK" : "Action"}</span>
        <div>
          <strong>${escapeHtml(item.label || "Readiness check")}</strong>
          <small>${escapeHtml(`${item.status || "Check"} - ${item.action || "Review this item."}`)}</small>
        </div>
      </article>
    `).join("")
    : `<article class="readiness-row action"><span>Check</span><div><strong>Readiness unavailable</strong><small>Refresh the session and review .env configuration.</small></div></article>`;
}

function setStep(id, stateName) {
  const el = $(id);
  if (!el) return;
  el.classList.remove("active", "done", "blocked");
  if (stateName) el.classList.add(stateName);
}

function setActiveView(viewId) {
  state.activeView = viewId;
  document.querySelectorAll(".workspace-view").forEach((view) => {
    view.classList.toggle("active", view.id === viewId);
  });
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.viewTarget === viewId);
  });
}

function scrollWorkspaceIntoView() {
  document.querySelector(".workspace-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function updateBackToTopButton() {
  const button = $("backToTopBtn");
  if (!button) return;
  button.classList.toggle("visible", window.scrollY > 520);
}

function currentWebsiteUrl() {
  return state.audit?.audited_url || $("auditUrlInput").value.trim() || "";
}

function currentWebsiteLabel() {
  const raw = currentWebsiteUrl();
  if (!raw) return "Add a URL audit first";
  try {
    return new URL(raw.includes("://") ? raw : `https://${raw}`).origin;
  } catch {
    return raw;
  }
}

function updateGoogleLauncher() {
  const label = currentWebsiteLabel();
  $("launcherWebsite").textContent = label;
  $("launcherOAuth").href = state.session?.oauth_ready ? "/auth/google/start" : "#setup";
  $("launcherOAuth").classList.toggle("disabled", !state.session?.oauth_ready);
  $("launcherOAuth").querySelector("strong").textContent = state.session?.oauth_ready
    ? "1. Authorize Google"
    : "1. Platform OAuth needed";
  $("launcherOAuth").querySelector("small").textContent = state.session?.oauth_ready
    ? "Best path when the user already has GA4 or Search Console."
    : "For hosted SaaS, configure this once so users only see a consent screen.";
  $("launcherStatus").textContent = state.session?.connected
    ? "Google is authorized. Refresh properties after creating or verifying anything new."
    : state.session?.oauth_ready
      ? "Click Authorize Google first. If no properties appear, use the setup links below."
      : "This app can still audit the site. Hosted SaaS should configure one OAuth client before live Google connections.";
  renderSimulator();
}

const simulatorSteps = [
  {
    label: "Website",
    status: "Ready",
    title: "Start with a website URL",
    body: "The user starts from the website URL. No Google product knowledge is required.",
    primary: "Start demo setup",
    evidence: ["Website: {site}", "Mode: beginner-safe setup"],
  },
  {
    label: "Google",
    status: "Consent",
    title: "Mock Google permission screen",
    body: "In production, this opens the hosted OAuth consent screen. Here it is simulated so you can inspect the flow.",
    primary: "Continue as site owner",
    evidence: ["Access: Search Console read-only", "Access: GA4 read-only"],
  },
  {
    label: "Search Console",
    status: "Verify",
    title: "Add and verify site ownership",
    body: "If Search Console is missing, the user gets the official setup button and the website value to paste.",
    primary: "Mark Search Console verified",
    evidence: ["Property: {site}", "Ownership: verified"],
  },
  {
    label: "GA4",
    status: "Install",
    title: "Create GA4 and install a tag",
    body: "The user can use GA4 directly or Tag Manager. The app only needs property access after installation.",
    primary: "Mark GA4 installed",
    evidence: ["GA4 property created", "Google tag detected"],
  },
  {
    label: "Ready",
    status: "Unlocked",
    title: "Google data connection is ready",
    body: "The app can re-check properties and unlock the growth dashboard once real data exists.",
    primary: "Load sample growth dashboard",
    evidence: ["Clicks, impressions, CTR, and position unlocked", "Sessions and channel mix unlocked"],
  },
];

function simulatorSite() {
  const label = currentWebsiteLabel();
  return label === "Add a URL audit first" ? "https://demo-store.example" : label;
}

function renderSimulator() {
  if (!$("simTimeline")) return;
  const step = simulatorSteps[state.simulatorStep] || simulatorSteps[0];
  const site = simulatorSite();
  $("simStageLabel").textContent = `Step ${state.simulatorStep + 1} of ${simulatorSteps.length}`;
  $("simStatusLabel").textContent = step.status;
  $("simTitle").textContent = step.title;
  $("simBody").textContent = step.body;
  $("simPrimaryBtn").textContent = step.primary;
  $("simBackBtn").disabled = state.simulatorStep === 0;
  $("simEvidence").innerHTML = step.evidence.map((item) => `
    <article><span>${escapeHtml(item.replace("{site}", site))}</span></article>
  `).join("");
  $("simTimeline").innerHTML = simulatorSteps.map((item, index) => {
    const stateName = index < state.simulatorStep ? "done" : index === state.simulatorStep ? "active" : "";
    return `
      <button class="sim-timeline-step ${stateName}" type="button" data-sim-step="${index}">
        <span>${String(index + 1).padStart(2, "0")}</span>
        <strong>${escapeHtml(item.label)}</strong>
        <small>${escapeHtml(item.status)}</small>
      </button>
    `;
  }).join("");
}

function setSimulatorStep(step) {
  state.simulatorStep = Math.max(0, Math.min(simulatorSteps.length - 1, step));
  renderSimulator();
}

function advanceSimulator() {
  if (state.simulatorStep < simulatorSteps.length - 1) {
    setSimulatorStep(state.simulatorStep + 1);
    showToast("Demo setup advanced.");
    return;
  }
  loadDemo().then(() => {
    showToast("Simulated Google setup completed. Sample dashboard unlocked.");
  }).catch((error) => showToast(error.message, "error"));
}

function updateSteps() {
  setStep("stepAudit", state.audit ? "done" : "active");
  setStep("stepGoogle", !state.session?.oauth_ready ? "blocked" : state.session?.connected ? "done" : state.audit ? "active" : "");
  const hasProps = (state.connections?.search_console_sites || []).length && (state.connections?.ga4_properties || []).length;
  setStep("stepProperties", hasProps ? "done" : state.session?.connected ? "active" : "");
  setStep("stepDashboard", state.report ? "done" : hasProps ? "active" : "");
}

function renderSession(session) {
  state.session = session;
  $("daysInput").value = session.report_days || 30;
  $("lagInput").value = session.lag_days || 2;
  $("connectBtn").href = session.oauth_ready ? "/auth/google/start" : "#setup";
  $("connectBtn").setAttribute("aria-disabled", "false");
  $("connectBtn").classList.toggle("disabled", false);
  $("googleStatusLabel").textContent = session.connected ? "Connected" : session.oauth_ready ? "Not connected" : "Optional setup";
  $("sessionStatus").textContent = session.connected
    ? "Google is connected. Refresh properties if permissions changed."
    : session.oauth_ready
      ? "Connect Google to auto-discover GA4 and Search Console."
      : "Audit and sample data work now. Configure platform OAuth before live Google connections.";
  $("connectBtn").textContent = session.connected ? "Reconnect Google" : session.oauth_ready ? "Connect Google" : "View setup path";
  if (!session.oauth_ready) {
    $("stepGoogle").querySelector("small").textContent = "Hosted SaaS users should not see this. Configure OAuth once for the platform.";
  } else {
    $("stepGoogle").querySelector("small").textContent = "Use OAuth so the app can list GA4 and Search Console automatically.";
  }
  renderPlatformReadiness(session);
  updateGoogleLauncher();
  updateSteps();
}

function renderConnections(connections) {
  state.connections = connections;
  const gsc = connections.search_console_sites || [];
  const ga4 = connections.ga4_properties || [];
  $("gscSelect").innerHTML = gsc.length
    ? gsc.map((item) => option(item.site_url, `${item.site_url} (${item.permission_level || "permission"})`)).join("")
    : option("", "No Search Console sites found");
  $("ga4Select").innerHTML = ga4.length
    ? ga4.map((item) => option(item.property_id, item.label)).join("")
    : option("", "No GA4 properties found");
  updateSteps();
}

function renderAuditEmpty() {
  setExportReady(false);
  setActionExportReady();
  $("auditSummary").innerHTML = `
    <article class="empty-state">
      <strong>Run the first scan</strong>
      <p>This gives a beginner useful SEO and GEO feedback before Google data exists.</p>
    </article>
  `;
  $("noGoogleDeliverables").innerHTML = `
    <article><strong>Starter audit</strong><small>URL health, metadata, indexability, sitemap, GEO, and tag checks.</small></article>
    <article><strong>Setup plan</strong><small>Plain next steps for GA4 and Search Console later.</small></article>
  `;
  $("starterOfferName").textContent = "Starter SEO and GEO cleanup sprint";
  $("starterOfferSummary").textContent = "Run an audit to turn the URL-only scan into a copyable client proposal.";
  $("starterOfferTimeline").textContent = "Waiting for audit";
  $("starterOfferDeliverables").innerHTML = `
    <article><span>01</span><strong>SEO and GEO scorecard</strong></article>
    <article><span>02</span><strong>Measurement setup handoff</strong></article>
  `;
  $("starterOfferUpgrade").textContent = "Connect Google later to unlock verified performance data.";
  $("quickWinList").innerHTML = `
    <article class="empty-state">
      <strong>Immediate fixes will appear here</strong>
      <p>After the scan, this becomes a compact action list that can be sold before Google data exists.</p>
    </article>
  `;
  $("auditChecklist").innerHTML = "";
  renderGeoEmpty();
}

function renderGeoEmpty() {
  $("geoScore").textContent = "--";
  $("geoGrade").textContent = "Not scanned";
  $("geoSummary").textContent = "Run an audit to check whether the page is crawlable, structured, and citable enough for AI answer surfaces.";
  $("geoSignalPills").innerHTML = `
    <span>Schema</span>
    <span>Answers</span>
    <span>Trust</span>
  `;
  $("geoHighlights").innerHTML = `
    <article><span>Visible words</span><strong>--</strong><small>Crawlable text</small></article>
    <article><span>Schema types</span><strong>--</strong><small>JSON-LD or microdata</small></article>
    <article><span>Questions</span><strong>--</strong><small>Answer-led sections</small></article>
    <article><span>References</span><strong>--</strong><small>External source hosts</small></article>
  `;
  $("geoChecklist").innerHTML = `
    <article class="empty-state">
      <strong>GEO checks will appear here</strong>
      <p>The scan looks for answerability, structure, trust evidence, citations, search access, and optional llms.txt.</p>
    </article>
  `;
  renderContentBriefEmpty();
}

function renderContentBriefEmpty() {
  $("briefTitle").textContent = "Prompt-safe GEO content brief";
  $("briefAudience").textContent = "Run an audit to generate a deterministic content brief from page evidence.";
  $("briefTopic").textContent = "--";
  $("briefPageType").textContent = "Waiting for scan";
  $("briefSections").innerHTML = `
    <article class="empty-state">
      <strong>Writer recommendations will appear here</strong>
      <p>The brief turns audit gaps into section, schema, trust, and citation guidance.</p>
    </article>
  `;
  $("briefRecommendations").innerHTML = "";
  $("briefPrompt").textContent = "The prompt will appear after an audit runs.";
}

function renderContentBrief(brief) {
  if (!brief) {
    renderContentBriefEmpty();
    return;
  }
  $("briefTitle").textContent = brief.title || "Prompt-safe GEO content brief";
  $("briefAudience").textContent = brief.audience || "Editorial guidance generated from the audited page evidence.";
  $("briefTopic").textContent = brief.primary_topic || "--";
  $("briefPageType").textContent = brief.page_type || "general website page";
  const sections = brief.recommended_sections || [];
  $("briefSections").innerHTML = sections.length
    ? sections.map((item) => `
      <article>
        <span>${escapeHtml(item.priority || "Medium")}</span>
        <div>
          <strong>${escapeHtml(item.title || "Recommended section")}</strong>
          <small>${escapeHtml(item.reason || "Review this section.")}</small>
        </div>
      </article>
    `).join("")
    : `<article class="empty-state"><strong>No section gaps found</strong><p>Keep the page concise, factual, and easy to cite.</p></article>`;
  const recommendationGroups = [
    ["Schema", brief.schema_recommendations || []],
    ["Trust", brief.trust_recommendations || []],
    ["Citations", brief.citation_recommendations || []],
  ];
  $("briefRecommendations").innerHTML = recommendationGroups.map(([label, items]) => `
    <article>
      <span>${escapeHtml(label)}</span>
      <div>
        <strong>${escapeHtml((items || [])[0] || "Review this area.")}</strong>
        <small>${escapeHtml((items || []).slice(1, 3).join(" "))}</small>
      </div>
    </article>
  `).join("");
  $("briefPrompt").textContent = brief.safe_prompt || "No safe writer prompt generated.";
}

function renderGeoReport(geo) {
  if (!geo) {
    renderGeoEmpty();
    return;
  }
  const signals = geo.signals || {};
  const schemaTypes = signals.schema_types || [];
  const questions = signals.question_headings || [];
  const trustSignals = signals.trust_signals || [];
  const externalHosts = signals.external_hosts || [];
  const freshness = signals.date_modified || signals.date_published || "";
  $("geoScore").textContent = String(geo.score ?? "--");
  $("geoGrade").textContent = geo.grade || "Scanned";
  $("geoSummary").textContent = geo.summary || "GEO readiness scan completed.";
  $("geoSignalPills").innerHTML = [
    schemaTypes.length ? `${schemaTypes.length} schema` : "No schema",
    questions.length ? `${questions.length} questions` : "No Q&A",
    trustSignals.length || signals.author || signals.site_name ? "Trust signals" : "Trust gaps",
    freshness ? "Freshness signal" : "No date",
  ].map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  $("geoHighlights").innerHTML = [
    {
      label: "Visible words",
      value: compactNumber(signals.visible_word_count),
      note: "Crawlable page text",
    },
    {
      label: "Schema types",
      value: schemaTypes.length ? schemaTypes.slice(0, 2).join(", ") : "None",
      note: schemaTypes.length > 2 ? `${schemaTypes.length - 2} more detected` : "Structured data",
    },
    {
      label: "Questions",
      value: compactNumber(questions.length),
      note: questions[0] || "Answer-led headings",
    },
    {
      label: "References",
      value: compactNumber(externalHosts.length),
      note: externalHosts[0] || "External source hosts",
    },
  ].map((item) => `
    <article>
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <small>${escapeHtml(item.note)}</small>
    </article>
  `).join("");
  $("geoChecklist").innerHTML = (geo.checks || []).map((check) => `
    <article class="geo-check-row ${check.ok ? "ok" : "gap"}">
      <span>${check.ok ? "OK" : check.experimental ? "Optional" : "Fix"}</span>
      <div>
        <strong>${escapeHtml(check.label)}</strong>
        <small>${escapeHtml(check.ok ? `+${check.weight} GEO points` : check.fix)}</small>
      </div>
    </article>
  `).join("");
  renderContentBrief(geo.content_brief);
}

function renderAudit(audit) {
  state.audit = audit;
  setExportReady(true);
  setActionExportReady();
  $("auditScore").textContent = String(audit.score ?? "--");
  $("auditGrade").textContent = audit.grade || "Scanned";
  renderGeoReport(audit.geo_report);
  $("auditStatusLabel").textContent = audit.grade || "Scanned";
  $("auditStatusNote").textContent = audit.audited_url || "Audit completed";
  const summary = audit.summary || {};
  const title = summary.title || "No title found";
  const description = summary.description || "No meta description found";
  const htmlSize = Number.isFinite(Number(summary.html_kb)) ? kilobytes(summary.html_kb) : "-";
  const responseTime = milliseconds(summary.response_time_ms);
  const robotsLabel = robotsAccessLabel(summary.robots_access);
  const robotsNote = robotsAccessNote(summary.robots_access);
  const xRobotsStatus = summary.x_robots_tag || {};
  const xRobotsStatusLabel = xRobotsLabel(xRobotsStatus);
  const xRobotsStatusNote = xRobotsNote(xRobotsStatus);
  const canonicalStatus = summary.canonical_status || {};
  const canonicalStatusLabel = canonicalLabel(canonicalStatus);
  const canonicalStatusNote = canonicalNote(canonicalStatus);
  const sitemapCoverage = summary.sitemap_coverage || {};
  const sitemapCoverageStatus = sitemapCoverageLabel(sitemapCoverage);
  const sitemapCoverageReason = sitemapCoverageNote(sitemapCoverage);
  const jsonLdStatus = jsonLdLabel(summary);
  const jsonLdStatusNote = jsonLdNote(summary);
  $("auditSummary").innerHTML = `
    <article>
      <span>Audited URL</span>
      <strong>${escapeHtml(audit.audited_url || "-")}</strong>
      <small>${escapeHtml(summary.redirected ? "Final URL after redirects" : "Requested URL")}</small>
    </article>
    <article>
      <span>Title</span>
      <strong>${escapeHtml(title)}</strong>
      <small>${escapeHtml(String(summary.title_length || 0))} characters</small>
    </article>
    <article>
      <span>Description</span>
      <strong>${escapeHtml(description)}</strong>
      <small>${escapeHtml(String(summary.description_length || 0))} characters</small>
    </article>
    <article>
      <span>Canonical</span>
      <strong>${escapeHtml(canonicalStatusLabel)}</strong>
      <small>${escapeHtml(canonicalStatusNote)}</small>
    </article>
    <article>
      <span>Google tag</span>
      <strong>${summary.ga4_detected || summary.gtm_detected ? "Detected" : "Not detected"}</strong>
      <small>GA4/GTM detection is a hint, not final proof.</small>
    </article>
    <article>
      <span>Robots access</span>
      <strong>${escapeHtml(robotsLabel)}</strong>
      <small>${escapeHtml(robotsNote)}</small>
    </article>
    <article>
      <span>X-Robots-Tag</span>
      <strong>${escapeHtml(xRobotsStatusLabel)}</strong>
      <small>${escapeHtml(xRobotsStatusNote)}</small>
    </article>
    <article>
      <span>Initial response</span>
      <strong>${escapeHtml(responseTime)}</strong>
      <small>Measured from the HTML request.</small>
    </article>
    <article>
      <span>HTML payload</span>
      <strong>${escapeHtml(htmlSize)}</strong>
      <small>${escapeHtml(summary.content_type || "Content type not detected")}</small>
    </article>
    <article>
      <span>Sitemap coverage</span>
      <strong>${escapeHtml(sitemapCoverageStatus)}</strong>
      <small>${escapeHtml(sitemapCoverageReason)}</small>
    </article>
    <article>
      <span>JSON-LD</span>
      <strong>${escapeHtml(jsonLdStatus)}</strong>
      <small>${escapeHtml(jsonLdStatusNote)}</small>
    </article>
    <article>
      <span>HTTP status</span>
      <strong>${escapeHtml(String(audit.status_code || "-"))}</strong>
      <small>${escapeHtml(summary.redirected ? "Final response after redirects." : "Initial URL response.")}</small>
    </article>
  `;
  const report = audit.no_google_report || {};
  const offer = report.starter_offer || {};
  const deliverables = report.what_you_can_sell_now || [];
  $("noGoogleSummary").textContent = report.positioning || "Use this as the first deliverable before Google data exists.";
  $("noGoogleDeliverables").innerHTML = deliverables.map((item) => `
    <article><strong>${escapeHtml(item)}</strong><small>Available from URL-only audit mode.</small></article>
  `).join("");
  $("starterOfferName").textContent = offer.name || "Starter SEO and GEO cleanup sprint";
  $("starterOfferSummary").textContent = offer.summary || "Package the URL-only audit into a practical SEO and GEO cleanup proposal.";
  $("starterOfferTimeline").textContent = offer.timeline || "Audit now; measurement follow-up after Google data accrues.";
  $("starterOfferDeliverables").innerHTML = (offer.deliverables || deliverables).map((item, index) => `
    <article>
      <span>${String(index + 1).padStart(2, "0")}</span>
      <strong>${escapeHtml(item)}</strong>
    </article>
  `).join("");
  $("starterOfferUpgrade").textContent = offer.upgrade_trigger || "Connect Google later for verified growth reporting.";
  const quickWins = audit.quick_wins || [];
  $("quickWinList").innerHTML = quickWins.length
    ? quickWins.map((item) => `
      <article>
        <span>${escapeHtml(item.impact || "Medium")}</span>
        <div>
          <strong>${escapeHtml(item.title || "SEO fix")}</strong>
          <small>${escapeHtml(item.action || "Review this item.")}</small>
        </div>
      </article>
    `).join("")
    : `<article class="empty-state"><strong>No urgent quick wins found</strong><p>The URL audit did not find a high-priority no-Google fix.</p></article>`;
  $("auditChecklist").innerHTML = (audit.checks || []).map((check) => `
    <article class="check-row ${check.ok ? "ok" : "gap"}">
      <span>${check.ok ? "OK" : "Fix"}</span>
      <div>
        <strong>${escapeHtml(check.label)}</strong>
        <small>${escapeHtml(check.ok ? `+${check.weight} readiness points` : check.fix)}</small>
      </div>
    </article>
  `).join("");
  updateSteps();
  setActiveView("auditView");
}

function channelName(row) {
  return row?.dimensions?.sessionDefaultChannelGroup || "-";
}

function rowMetric(row, key) {
  return Number(row?.metrics?.[key] || 0);
}

function renderMetricCards(report) {
  const gsc = report.gsc || {};
  const summary = gsc.summary || {};
  const trends = gsc.trends || {};
  const score = report.scorecard || {};
  const metrics = score.metrics || {};
  const diagnosis = score.diagnosis || {};
  $("metricClicks").textContent = compactNumber(summary.clicks);
  $("metricImpressions").textContent = compactNumber(summary.impressions);
  $("metricCtr").textContent = percent(summary.ctr);
  $("metricPosition").textContent = summary.position ? Number(summary.position).toFixed(1) : "-";
  $("metricOrganicSessions").textContent = compactNumber(metrics.organic_sessions);
  $("metricRevenue").textContent = currency(metrics.revenue);
  $("metricClicksNote").textContent = trendLabel(trends.clicks) || "Search Console";
  $("metricImpressionsNote").textContent = trendLabel(trends.impressions) || "Google visibility";
  $("metricCtrNote").textContent = trendLabel(trends.ctr) || "Clicks / impressions";
  $("metricPositionNote").textContent = trendLabel(trends.position, true) || "Weighted by impressions";
  $("metricRevenueNote").textContent = diagnosis.revenue_label || "GA4 ecommerce";
  $("scopeLabel").textContent = report.target_scope?.label || "Site-wide";
  $("periodLabel").textContent = score.period_label || "No report loaded";
}

function renderChannelBars(report) {
  const mix = report.scorecard?.metrics?.channel_mix || {};
  const rows = [
    ["Organic Search", mix.organic || 0],
    ["Direct", mix.direct || 0],
    ["Referral", mix.referral || 0],
    ["Social", mix.social || 0],
  ];
  $("channelBars").innerHTML = rows.map(([label, share]) => `
    <article class="bar-row">
      <div><strong>${escapeHtml(label)}</strong><span>${percent(share, 0)}</span></div>
      <i><b style="width:${Math.max(0, Math.min(100, share * 100))}%"></b></i>
    </article>
  `).join("");
}

function opportunityMeta(row) {
  return [
    `${compactNumber(row.clicks)} clicks`,
    `${compactNumber(row.impressions)} impressions`,
    `CTR ${percent(row.ctr)}`,
    `Pos ${Number(row.position || 0).toFixed(1)}`,
    row.missed_clicks ? `~${compactNumber(row.missed_clicks)} missed clicks` : "",
  ].filter(Boolean).join(" | ");
}

function renderOpportunityList(id, rows, titleKey, emptyText) {
  const values = Array.isArray(rows) ? rows : [];
  $(id).innerHTML = values.length
    ? values.slice(0, 8).map((row, index) => `
      <article class="opportunity-row">
        <span>${String(index + 1).padStart(2, "0")}</span>
        <div>
          <strong>${escapeHtml(row[titleKey] || row.label || "-")}</strong>
          <small>${escapeHtml(opportunityMeta(row))}</small>
        </div>
        <em>${escapeHtml(row.opportunity_score ?? "-")}</em>
      </article>
    `).join("")
    : `<article class="opportunity-row muted"><span>--</span><div><strong>${escapeHtml(emptyText)}</strong><small>Try a broader URL scope or lower the threshold.</small></div></article>`;
}

function renderBuckets(rows) {
  const values = Array.isArray(rows) ? rows : [];
  $("bucketList").innerHTML = values.length
    ? values.map((row) => {
      const share = Number(row.share || 0);
      return `
        <article class="bucket-row">
          <div>
            <strong>${escapeHtml(row.label || "-")}</strong>
            <small>${compactNumber(row.query_count)} queries | ${compactNumber(row.impressions)} impressions</small>
          </div>
          <span>${percent(share, 0)}</span>
          <i><b style="width:${Math.max(0, Math.min(100, share * 100))}%"></b></i>
        </article>
      `;
    }).join("")
    : `<article class="bucket-row"><div><strong>No ranking distribution yet</strong><small>Search Console query rows are required.</small></div></article>`;
}

function renderDataList(id, rows, mapper, emptyText) {
  const values = Array.isArray(rows) ? rows : [];
  $(id).innerHTML = values.length
    ? values.map((row) => {
      const item = mapper(row);
      return `
        <article class="data-row">
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(item.meta)}</small>
          </div>
          <span>${escapeHtml(item.value)}</span>
        </article>
      `;
    }).join("")
    : `<article class="data-row muted"><div><strong>${escapeHtml(emptyText)}</strong><small>Run a report after connecting Google.</small></div></article>`;
}

function renderTables(report) {
  const gsc = report.gsc || {};
  const ga4 = report.ga4 || {};
  renderDataList("queryTable", gsc.top_queries || [], (row) => ({
    title: row.query || "-",
    meta: `${compactNumber(row.clicks)} clicks | ${compactNumber(row.impressions)} impressions | CTR ${percent(row.ctr)} | Pos ${Number(row.position || 0).toFixed(1)}`,
    value: `${compactNumber(row.impressions)} imp`,
  }), "No query rows");
  renderDataList("pageTable", gsc.top_pages || [], (row) => ({
    title: row.page || "-",
    meta: `${compactNumber(row.clicks)} clicks | CTR ${percent(row.ctr)} | Pos ${Number(row.position || 0).toFixed(1)}`,
    value: `${compactNumber(row.impressions)} imp`,
  }), "No page rows");
  renderDataList("channelTable", ga4.channel_groups || [], (row) => ({
    title: channelName(row),
    meta: `${compactNumber(rowMetric(row, "totalUsers"))} users | ${compactNumber(rowMetric(row, "engagedSessions"))} engaged sessions`,
    value: `${compactNumber(rowMetric(row, "sessions"))} sessions`,
  }), "No GA4 channels");
  renderDataList("landingTable", ga4.landing_pages || [], (row) => ({
    title: row.dimensions?.landingPagePlusQueryString || row.dimensions?.landingPage || "-",
    meta: `${compactNumber(rowMetric(row, "screenPageViews"))} views | ${compactNumber(rowMetric(row, "engagedSessions"))} engaged sessions`,
    value: `${compactNumber(rowMetric(row, "sessions"))} sessions`,
  }), "No landing pages");
}

function renderGrowthSourceBadges(report) {
  if (!$("growthSourceBadges")) return;
  const status = report?.scorecard?.source_status || {};
  const items = [
    {
      key: "gsc",
      label: "Search Console",
      ok: Boolean(status.gsc),
      note: sourceStatusText(report, "gsc"),
    },
    {
      key: "ga4",
      label: "GA4 traffic",
      ok: Boolean(status.ga4),
      note: sourceStatusText(report, "ga4"),
    },
    {
      key: "ecommerce",
      label: "Revenue",
      ok: Boolean(status.ecommerce),
      note: sourceStatusText(report, "ecommerce"),
    },
  ];
  $("growthSourceBadges").innerHTML = items.map((item) => `
    <article class="source-badge ${item.ok ? "ok" : "waiting"}">
      <span>${item.ok ? "OK" : "Waiting"}</span>
      <div>
        <strong>${escapeHtml(item.label)}</strong>
        <small>${escapeHtml(item.note)}</small>
      </div>
    </article>
  `).join("");
}

function renderGrowthReportEmpty() {
  setGrowthExportReady(false);
  setActionExportReady();
  $("metricClicks").textContent = "-";
  $("metricImpressions").textContent = "-";
  $("metricCtr").textContent = "-";
  $("metricPosition").textContent = "-";
  $("metricOrganicSessions").textContent = "-";
  $("metricRevenue").textContent = "-";
  $("metricClicksNote").textContent = "Search Console";
  $("metricImpressionsNote").textContent = "Google visibility";
  $("metricCtrNote").textContent = "Clicks / impressions";
  $("metricPositionNote").textContent = "Weighted by impressions";
  $("metricRevenueNote").textContent = "GA4 ecommerce";
  renderGrowthSourceBadges(null);
}

function renderReport(report) {
  state.report = report;
  setGrowthExportReady(true);
  setActionExportReady();
  renderGrowthSourceBadges(report);
  renderMetricCards(report);
  renderChannelBars(report);
  const opp = report.opportunities || {};
  renderOpportunityList("rankingList", opp.low_hanging_queries || [], "query", "No ranking wins found");
  renderOpportunityList("ctrList", opp.ctr_opportunities || [], "query", "No CTR rewrite candidates");
  renderOpportunityList("pageList", opp.page_opportunities || [], "page", "No page-level opportunities");
  renderBuckets(opp.rank_buckets || []);
  renderTables(report);
  updateSteps();
  setActiveView("dashboardView");
}

async function refreshSession() {
  const payload = await api("/api/session");
  renderSession(payload);
  if (payload.connected) {
    await refreshConnections();
  }
}

async function refreshConnections() {
  $("refreshConnectionsBtn").disabled = true;
  try {
    const payload = await api("/api/connections");
    renderConnections(payload);
    showToast("Google properties refreshed.");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    $("refreshConnectionsBtn").disabled = false;
  }
}

async function runAudit(event) {
  event.preventDefault();
  const rawUrl = $("auditUrlInput").value.trim();
  if (!rawUrl) {
    showToast("Enter a URL first.", "error");
    return;
  }
  $("auditBtn").disabled = true;
  $("auditBtn").textContent = "Scanning...";
  try {
    const payload = await api("/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: rawUrl }),
    });
    renderAudit(payload);
    if (!$("targetInput").value) $("targetInput").value = payload.audited_url || rawUrl;
    updateGoogleLauncher();
    showToast("Instant audit completed.");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    $("auditBtn").disabled = false;
    $("auditBtn").textContent = "Run instant audit";
  }
}

async function loadSampleAudit() {
  $("sampleAuditBtn").disabled = true;
  $("sampleAuditBtn").textContent = "Loading...";
  try {
    const payload = await api("/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ demo: true }),
    });
    $("auditUrlInput").value = payload.audited_url || "https://demo.open-seo-growth.local/classes/beginner-sourdough";
    renderAudit(payload);
    if (!$("targetInput").value) $("targetInput").value = payload.audited_url || "";
    updateGoogleLauncher();
    showToast("Sample SEO/GEO audit loaded.");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    $("sampleAuditBtn").disabled = false;
    $("sampleAuditBtn").textContent = "Load sample audit";
  }
}

async function runAnalysis(event) {
  event.preventDefault();
  $("analyzeBtn").disabled = true;
  $("analyzeBtn").textContent = "Analyzing...";
  try {
    const payload = await api("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gsc_site_url: $("gscSelect").value,
        ga4_property_id: $("ga4Select").value,
        target_url: $("targetInput").value,
        days: Number($("daysInput").value || 30),
        lag_days: Number($("lagInput").value || 2),
      }),
    });
    renderReport(payload);
    showToast(payload.demo ? "Sample report loaded." : "Live report updated.");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    $("analyzeBtn").disabled = false;
    $("analyzeBtn").textContent = "Run growth report";
  }
}

async function loadDemo() {
  const payload = await api("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ demo: true }),
  });
  renderReport(payload);
  showToast("Sample report loaded.");
}

async function copyWebsite() {
  const value = currentWebsiteLabel();
  if (!value || value === "Add a URL audit first") {
    showToast("Run an audit or enter a website URL first.", "error");
    return;
  }
  try {
    await navigator.clipboard.writeText(value);
    showToast("Website copied for Google setup.");
  } catch {
    showToast(value);
  }
}

async function copyReadinessChecklist() {
  if (!state.session) {
    showToast("Session is still loading. Try again in a moment.", "error");
    return;
  }
  try {
    await navigator.clipboard.writeText(buildPlatformReadinessMarkdown(state.session));
    showToast("Platform readiness checklist copied.");
  } catch {
    showToast("Clipboard is unavailable. Review the checklist on screen.", "error");
  }
}

async function copyAuditMarkdown() {
  if (!state.audit) {
    showToast("Run an audit first.", "error");
    return;
  }
  const markdown = buildAuditMarkdown(state.audit);
  try {
    await navigator.clipboard.writeText(markdown);
    showToast("Audit report copied as Markdown.");
  } catch {
    showToast("Clipboard is unavailable. Download the Markdown file instead.", "error");
  }
}

function downloadAuditMarkdown() {
  if (!state.audit) {
    showToast("Run an audit first.", "error");
    return;
  }
  const slug = fileSlug(state.audit.audited_url);
  downloadText(`${slug}-seo-geo-audit-${isoDate()}.md`, buildAuditMarkdown(state.audit), "text/markdown;charset=utf-8");
  showToast("Markdown report downloaded.");
}

function downloadAuditBrief() {
  if (!state.audit) {
    showToast("Run an audit first.", "error");
    return;
  }
  const slug = fileSlug(state.audit.audited_url);
  downloadText(`${slug}-geo-content-brief-${isoDate()}.md`, buildBriefMarkdown(state.audit), "text/markdown;charset=utf-8");
  showToast("GEO content brief downloaded.");
}

function downloadAuditJson() {
  if (!state.audit) {
    showToast("Run an audit first.", "error");
    return;
  }
  const slug = fileSlug(state.audit.audited_url);
  const payload = {
    exported_at: new Date().toISOString(),
    generator: "Open SEO Growth",
    audit: state.audit,
  };
  downloadText(`${slug}-seo-geo-audit-${isoDate()}.json`, JSON.stringify(payload, null, 2), "application/json;charset=utf-8");
  showToast("JSON evidence downloaded.");
}

async function copyStarterOffer() {
  if (!state.audit) {
    showToast("Run an audit first.", "error");
    return;
  }
  try {
    await navigator.clipboard.writeText(buildStarterOfferMarkdown(state.audit));
    showToast("Starter proposal copied as Markdown.");
  } catch {
    showToast("Clipboard is unavailable. Download the proposal instead.", "error");
  }
}

function downloadStarterOffer() {
  if (!state.audit) {
    showToast("Run an audit first.", "error");
    return;
  }
  const slug = fileSlug(state.audit.audited_url);
  downloadText(`${slug}-starter-seo-geo-proposal-${isoDate()}.md`, buildStarterOfferMarkdown(state.audit), "text/markdown;charset=utf-8");
  showToast("Starter proposal downloaded.");
}

async function copyGrowthReportMarkdown() {
  if (!state.report) {
    showToast("Run a growth report first.", "error");
    return;
  }
  try {
    await navigator.clipboard.writeText(buildGrowthReportMarkdown(state.report));
    showToast("Growth report copied as Markdown.");
  } catch {
    showToast("Clipboard is unavailable. Download the Markdown file instead.", "error");
  }
}

function downloadGrowthMarkdown() {
  if (!state.report) {
    showToast("Run a growth report first.", "error");
    return;
  }
  downloadText(`${growthReportSlug(state.report)}-${isoDate()}.md`, buildGrowthReportMarkdown(state.report), "text/markdown;charset=utf-8");
  showToast("Growth Markdown report downloaded.");
}

function downloadGrowthJson() {
  if (!state.report) {
    showToast("Run a growth report first.", "error");
    return;
  }
  const payload = {
    exported_at: new Date().toISOString(),
    generator: "Open SEO Growth",
    report: state.report,
  };
  downloadText(`${growthReportSlug(state.report)}-${isoDate()}.json`, JSON.stringify(payload, null, 2), "application/json;charset=utf-8");
  showToast("Growth JSON report downloaded.");
}

async function copyActionQueue() {
  const rows = buildActionRows();
  if (!rows.length) {
    showToast("Run an audit or growth report first.", "error");
    return;
  }
  try {
    await navigator.clipboard.writeText(buildActionQueueMarkdown());
    showToast("Action queue copied as Markdown.");
  } catch {
    showToast("Clipboard is unavailable. Download the task queue instead.", "error");
  }
}

function downloadActionCsv() {
  const rows = buildActionRows();
  if (!rows.length) {
    showToast("Run an audit or growth report first.", "error");
    return;
  }
  downloadText(`${actionQueueSlug()}-${isoDate()}.csv`, buildActionQueueCsv(), "text/csv;charset=utf-8");
  showToast("Action queue CSV downloaded.");
}

function downloadActionMarkdown() {
  const rows = buildActionRows();
  if (!rows.length) {
    showToast("Run an audit or growth report first.", "error");
    return;
  }
  downloadText(`${actionQueueSlug()}-${isoDate()}.md`, buildActionQueueMarkdown(), "text/markdown;charset=utf-8");
  showToast("Action queue Markdown downloaded.");
}

function wireEvents() {
  $("auditForm").addEventListener("submit", runAudit);
  $("auditUrlInput").addEventListener("input", updateGoogleLauncher);
  $("analysisForm").addEventListener("submit", runAnalysis);
  $("refreshConnectionsBtn").addEventListener("click", refreshConnections);
  $("demoBtn").addEventListener("click", loadDemo);
  $("sampleAuditBtn").addEventListener("click", loadSampleAudit);
  $("copyWebsiteBtn").addEventListener("click", copyWebsite);
  $("copyReadinessBtn").addEventListener("click", copyReadinessChecklist);
  $("copyReportBtn").addEventListener("click", copyAuditMarkdown);
  $("downloadMarkdownBtn").addEventListener("click", downloadAuditMarkdown);
  $("downloadBriefBtn").addEventListener("click", downloadAuditBrief);
  $("downloadJsonBtn").addEventListener("click", downloadAuditJson);
  $("copyStarterOfferBtn").addEventListener("click", copyStarterOffer);
  $("downloadStarterOfferBtn").addEventListener("click", downloadStarterOffer);
  $("copyGrowthReportBtn").addEventListener("click", copyGrowthReportMarkdown);
  $("downloadGrowthMarkdownBtn").addEventListener("click", downloadGrowthMarkdown);
  $("downloadGrowthJsonBtn").addEventListener("click", downloadGrowthJson);
  $("copyActionQueueBtn").addEventListener("click", copyActionQueue);
  $("downloadActionCsvBtn").addEventListener("click", downloadActionCsv);
  $("downloadActionMarkdownBtn").addEventListener("click", downloadActionMarkdown);
  $("simPrimaryBtn").addEventListener("click", advanceSimulator);
  $("simBackBtn").addEventListener("click", () => setSimulatorStep(state.simulatorStep - 1));
  $("simResetBtn").addEventListener("click", () => {
    setSimulatorStep(0);
    showToast("Demo setup reset.");
  });
  $("simTimeline").addEventListener("click", (event) => {
    const button = event.target.closest("[data-sim-step]");
    if (!button) return;
    setSimulatorStep(Number(button.dataset.simStep));
  });
  $("launcherRetestBtn").addEventListener("click", () => {
    refreshSession()
      .then(() => showToast("Google setup status refreshed."))
      .catch((error) => showToast(error.message, "error"));
  });
  $("launcherOAuth").addEventListener("click", (event) => {
    if (state.session && !state.session.oauth_ready) {
      event.preventDefault();
      showToast("Platform OAuth is not configured yet. Use the setup links for now.");
    }
  });
  $("connectBtn").addEventListener("click", (event) => {
    if (state.session && !state.session.oauth_ready) {
      event.preventDefault();
      setActiveView("setupView");
      scrollWorkspaceIntoView();
      showToast("Google can be added later. Start with the audit, then follow the setup path.");
    }
  });
  $("topJumpBtn").addEventListener("click", () => {
    setActiveView("auditView");
    $("audit").scrollIntoView({ behavior: "smooth", block: "start" });
    $("auditUrlInput").focus({ preventScroll: true });
  });
  $("backToTopBtn").addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    $("auditUrlInput").focus({ preventScroll: true });
  });
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveView(button.dataset.viewTarget);
      scrollWorkspaceIntoView();
    });
  });
  window.addEventListener("scroll", updateBackToTopButton, { passive: true });
}

renderAuditEmpty();
renderGrowthReportEmpty();
wireEvents();
updateGoogleLauncher();
updateBackToTopButton();
renderSimulator();
refreshSession().catch((error) => showToast(error.message, "error"));
