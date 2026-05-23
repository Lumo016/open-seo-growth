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
      : "This prototype can still audit the site. Hosted SaaS should configure one OAuth client before live Google connections.";
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
  $("geoScore").textContent = String(geo.score ?? "--");
  $("geoGrade").textContent = geo.grade || "Scanned";
  $("geoSummary").textContent = geo.summary || "GEO readiness scan completed.";
  $("geoSignalPills").innerHTML = [
    schemaTypes.length ? `${schemaTypes.length} schema` : "No schema",
    questions.length ? `${questions.length} questions` : "No Q&A",
    trustSignals.length || signals.author || signals.site_name ? "Trust signals" : "Trust gaps",
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
}

function renderAudit(audit) {
  state.audit = audit;
  $("auditScore").textContent = String(audit.score ?? "--");
  $("auditGrade").textContent = audit.grade || "Scanned";
  renderGeoReport(audit.geo_report);
  $("auditStatusLabel").textContent = audit.grade || "Scanned";
  $("auditStatusNote").textContent = audit.audited_url || "Audit completed";
  const summary = audit.summary || {};
  const title = summary.title || "No title found";
  const description = summary.description || "No meta description found";
  $("auditSummary").innerHTML = `
    <article>
      <span>Audited URL</span>
      <strong>${escapeHtml(audit.audited_url || "-")}</strong>
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
      <span>Google tag</span>
      <strong>${summary.ga4_detected || summary.gtm_detected ? "Detected" : "Not detected"}</strong>
      <small>GA4/GTM detection is a hint, not final proof.</small>
    </article>
  `;
  const report = audit.no_google_report || {};
  const deliverables = report.what_you_can_sell_now || [];
  $("noGoogleSummary").textContent = report.positioning || "Use this as the first deliverable before Google data exists.";
  $("noGoogleDeliverables").innerHTML = deliverables.map((item) => `
    <article><strong>${escapeHtml(item)}</strong><small>Available from URL-only audit mode.</small></article>
  `).join("");
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

function renderReport(report) {
  state.report = report;
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

function wireEvents() {
  $("auditForm").addEventListener("submit", runAudit);
  $("auditUrlInput").addEventListener("input", updateGoogleLauncher);
  $("analysisForm").addEventListener("submit", runAnalysis);
  $("refreshConnectionsBtn").addEventListener("click", refreshConnections);
  $("demoBtn").addEventListener("click", loadDemo);
  $("copyWebsiteBtn").addEventListener("click", copyWebsite);
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
      document.querySelector(".workspace-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" });
      showToast("Google can be added later. Start with the audit, then follow the setup path.");
    }
  });
  $("topJumpBtn").addEventListener("click", () => {
    setActiveView("auditView");
    $("audit").scrollIntoView({ behavior: "smooth", block: "start" });
    $("auditUrlInput").focus({ preventScroll: true });
  });
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => setActiveView(button.dataset.viewTarget));
  });
}

renderAuditEmpty();
wireEvents();
updateGoogleLauncher();
renderSimulator();
refreshSession().catch((error) => showToast(error.message, "error"));
