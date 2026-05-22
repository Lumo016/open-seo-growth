from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote, urlparse

from google.auth.transport.requests import AuthorizedSession

from .config import Settings
from .opportunities import opportunity_engine, percent_change, safe_float


def date_windows(days: int, lag_days: int) -> dict[str, dict[str, str]]:
    day_count = max(7, min(180, int(days)))
    lag_count = max(0, min(7, int(lag_days)))
    current_end = datetime.utcnow().date() - timedelta(days=lag_count)
    current_start = current_end - timedelta(days=day_count - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=day_count - 1)
    return {
        "current": {"start_date": current_start.isoformat(), "end_date": current_end.isoformat()},
        "previous": {"start_date": previous_start.isoformat(), "end_date": previous_end.isoformat()},
    }


def normalize_target_scope(value: str | None, fallback_site: str | None = None) -> dict[str, str]:
    raw = (value or fallback_site or "").strip()
    if not raw:
        return {"input": "", "url": "", "host": "", "path": "/", "mode": "site", "label": "Site-wide"}
    if raw.startswith("sc-domain:"):
        host = raw.replace("sc-domain:", "", 1)
        return {"input": raw, "url": raw, "host": host, "path": "/", "mode": "site", "label": "Domain property"}
    if raw.startswith("/") and fallback_site and fallback_site.startswith("http"):
        fallback = urlparse(fallback_site)
        raw = f"{fallback.scheme or 'https'}://{fallback.netloc}{raw}"
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    url = f"{parsed.scheme or 'https'}://{parsed.netloc}{path}{query}"
    is_root = path in {"", "/"} and not parsed.query
    return {
        "input": raw,
        "url": url,
        "host": parsed.netloc,
        "path": path,
        "mode": "site" if is_root else "page",
        "label": "Site-wide" if is_root else "Single page",
    }


def search_console_sites(session: AuthorizedSession) -> list[dict[str, Any]]:
    response = session.get("https://searchconsole.googleapis.com/webmasters/v3/sites", timeout=30)
    response.raise_for_status()
    entries = response.json().get("siteEntry", [])
    return [
        {
            "site_url": entry.get("siteUrl", ""),
            "permission_level": entry.get("permissionLevel", ""),
            "label": entry.get("siteUrl", ""),
        }
        for entry in entries
    ]


def ga4_properties(session: AuthorizedSession) -> list[dict[str, Any]]:
    properties: list[dict[str, Any]] = []
    endpoints = [
        "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
        "https://analyticsadmin.googleapis.com/v1alpha/accountSummaries",
    ]
    last_error: Exception | None = None
    for endpoint in endpoints:
        page_token = ""
        try:
            while True:
                params = {"pageSize": "200"}
                if page_token:
                    params["pageToken"] = page_token
                response = session.get(endpoint, params=params, timeout=30)
                response.raise_for_status()
                payload = response.json()
                for account in payload.get("accountSummaries", []):
                    account_name = account.get("displayName") or account.get("account") or "Google Analytics"
                    for prop in account.get("propertySummaries", []):
                        raw_property = prop.get("property", "")
                        property_id = raw_property.split("/")[-1]
                        properties.append(
                            {
                                "property_id": property_id,
                                "property_name": raw_property,
                                "display_name": prop.get("displayName") or property_id,
                                "account_name": account_name,
                                "label": f"{prop.get('displayName') or property_id} - {account_name}",
                            }
                        )
                page_token = payload.get("nextPageToken") or ""
                if not page_token:
                    return properties
        except Exception as exc:
            last_error = exc
            properties = []
            continue
    if last_error:
        raise last_error
    return properties


def list_connections(session: AuthorizedSession) -> dict[str, Any]:
    return {
        "search_console_sites": search_console_sites(session),
        "ga4_properties": ga4_properties(session),
    }


def gsc_page_filters(target_scope: dict[str, str]) -> list[dict[str, str]]:
    if target_scope.get("mode") != "page" or not target_scope.get("url"):
        return []
    return [{"dimension": "page", "operator": "equals", "expression": target_scope["url"]}]


def gsc_search_analytics(
    session: AuthorizedSession,
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: list[str] | None = None,
    row_limit: int = 100,
    filters: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    encoded_site = quote(site_url, safe="")
    payload: dict[str, Any] = {"startDate": start_date, "endDate": end_date, "rowLimit": row_limit}
    if dimensions:
        payload["dimensions"] = dimensions
    if filters:
        payload["dimensionFilterGroups"] = [{"groupType": "and", "filters": filters}]
    response = session.post(
        f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query",
        json=payload,
        timeout=45,
    )
    response.raise_for_status()
    return response.json().get("rows", [])


def gsc_summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    clicks = sum(safe_float(row.get("clicks")) for row in rows)
    impressions = sum(safe_float(row.get("impressions")) for row in rows)
    weighted_position = sum(safe_float(row.get("position")) * safe_float(row.get("impressions")) for row in rows)
    position = weighted_position / impressions if impressions else 0
    return {"clicks": clicks, "impressions": impressions, "ctr": clicks / impressions if impressions else 0, "position": position}


def dimension_rows(rows: list[dict[str, Any]], dimension_name: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        keys = row.get("keys") or []
        output.append(
            {
                dimension_name: keys[0] if keys else "",
                "clicks": safe_float(row.get("clicks")),
                "impressions": safe_float(row.get("impressions")),
                "ctr": safe_float(row.get("ctr")),
                "position": safe_float(row.get("position")),
            }
        )
    return output


def ga4_run_report(
    session: AuthorizedSession,
    property_id: str,
    start_date: str,
    end_date: str,
    metrics: list[str],
    dimensions: list[str] | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "metrics": [{"name": name} for name in metrics],
        "limit": str(limit),
    }
    if dimensions:
        body["dimensions"] = [{"name": name} for name in dimensions]
    response = session.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
        json=body,
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    dimension_headers = [item.get("name", "") for item in payload.get("dimensionHeaders", [])]
    metric_headers = [item.get("name", "") for item in payload.get("metricHeaders", [])]
    rows: list[dict[str, Any]] = []
    for row in payload.get("rows", []):
        rows.append(
            {
                "dimensions": {
                    name: (row.get("dimensionValues", [])[index] or {}).get("value", "")
                    for index, name in enumerate(dimension_headers)
                },
                "metrics": {
                    name: safe_float((row.get("metricValues", [])[index] or {}).get("value"))
                    for index, name in enumerate(metric_headers)
                },
            }
        )
    return rows


def first_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    return rows[0].get("metrics", {}) if rows else {}


def optional_report(label: str, errors: list[dict[str, str]], fn: Any) -> Any:
    try:
        return fn()
    except Exception as exc:
        errors.append({"report": label, "error": exc.__class__.__name__, "message": str(exc)})
        return []


def organic_sessions(channel_rows: list[dict[str, Any]]) -> float:
    total = 0.0
    for row in channel_rows:
        channel = (row.get("dimensions", {}).get("sessionDefaultChannelGroup") or "").lower()
        if "organic search" in channel:
            total += safe_float(row.get("metrics", {}).get("sessions"))
    return total


def traffic_channels(channel_rows: list[dict[str, Any]]) -> dict[str, float]:
    buckets = {"organic": 0.0, "direct": 0.0, "referral": 0.0, "social": 0.0}
    total = 0.0
    for row in channel_rows:
        channel = (row.get("dimensions", {}).get("sessionDefaultChannelGroup") or "").lower()
        sessions = safe_float(row.get("metrics", {}).get("sessions"))
        total += sessions
        if "organic search" in channel:
            buckets["organic"] += sessions
        elif "direct" in channel:
            buckets["direct"] += sessions
        elif "referral" in channel:
            buckets["referral"] += sessions
        elif "social" in channel:
            buckets["social"] += sessions
    return {key: (value / total if total else 0.0) for key, value in buckets.items()} | {"total": total}


def run_growth_report(
    session: AuthorizedSession,
    settings: Settings,
    *,
    gsc_site_url: str,
    ga4_property_id: str,
    target_url: str = "",
    days: int | None = None,
    lag_days: int | None = None,
) -> dict[str, Any]:
    report_days = days or settings.report_days
    report_lag = lag_days if lag_days is not None else settings.lag_days
    windows = date_windows(report_days, report_lag)
    current = windows["current"]
    previous = windows["previous"]
    target_scope = normalize_target_scope(target_url, gsc_site_url)
    filters = gsc_page_filters(target_scope)

    summary_rows = gsc_search_analytics(session, gsc_site_url, current["start_date"], current["end_date"], row_limit=1, filters=filters)
    previous_rows = gsc_search_analytics(session, gsc_site_url, previous["start_date"], previous["end_date"], row_limit=1, filters=filters)
    query_rows = gsc_search_analytics(session, gsc_site_url, current["start_date"], current["end_date"], ["query"], row_limit=20, filters=filters)
    page_rows = gsc_search_analytics(session, gsc_site_url, current["start_date"], current["end_date"], ["page"], row_limit=20, filters=filters)
    opportunity_query_rows = gsc_search_analytics(session, gsc_site_url, current["start_date"], current["end_date"], ["query"], row_limit=250, filters=filters)
    opportunity_page_rows = gsc_search_analytics(session, gsc_site_url, current["start_date"], current["end_date"], ["page"], row_limit=150, filters=filters)

    gsc_current = gsc_summary(summary_rows)
    gsc_previous = gsc_summary(previous_rows)
    gsc_queries = dimension_rows(query_rows, "query")
    gsc_pages = dimension_rows(page_rows, "page")
    opportunity_queries = dimension_rows(opportunity_query_rows, "query")
    opportunity_pages = dimension_rows(opportunity_page_rows, "page")

    ga4_errors: list[dict[str, str]] = []
    core_metrics = ["sessions", "totalUsers", "screenPageViews", "engagedSessions", "engagementRate", "eventCount"]
    ga4_current = first_metrics(
        ga4_run_report(session, ga4_property_id, current["start_date"], current["end_date"], core_metrics, limit=1)
    )
    ga4_previous = first_metrics(
        ga4_run_report(session, ga4_property_id, previous["start_date"], previous["end_date"], core_metrics, limit=1)
    )
    channel_groups = optional_report(
        "channel_groups",
        ga4_errors,
        lambda: ga4_run_report(
            session,
            ga4_property_id,
            current["start_date"],
            current["end_date"],
            ["sessions", "totalUsers", "engagedSessions", "eventCount"],
            ["sessionDefaultChannelGroup"],
            limit=12,
        ),
    )
    landing_pages = optional_report(
        "landing_pages",
        ga4_errors,
        lambda: ga4_run_report(
            session,
            ga4_property_id,
            current["start_date"],
            current["end_date"],
            ["sessions", "screenPageViews", "engagedSessions"],
            ["landingPagePlusQueryString"],
            limit=20,
        ),
    )
    events = optional_report(
        "events",
        ga4_errors,
        lambda: ga4_run_report(
            session,
            ga4_property_id,
            current["start_date"],
            current["end_date"],
            ["eventCount", "totalUsers"],
            ["eventName"],
            limit=20,
        ),
    )
    ecommerce = optional_report(
        "ecommerce",
        ga4_errors,
        lambda: first_metrics(
            ga4_run_report(
                session,
                ga4_property_id,
                current["start_date"],
                current["end_date"],
                ["ecommercePurchases", "purchaseRevenue"],
                limit=1,
            )
        ),
    )

    opportunities = opportunity_engine(opportunity_queries, opportunity_pages, min_impressions=settings.min_impressions)
    channels = traffic_channels(channel_groups if isinstance(channel_groups, list) else [])
    ecommerce_metrics = ecommerce if isinstance(ecommerce, dict) else {}
    source_status = {
        "gsc": bool(gsc_current.get("impressions")),
        "ga4": bool(ga4_current.get("sessions")),
        "ecommerce": bool(ecommerce_metrics.get("ecommercePurchases") or ecommerce_metrics.get("purchaseRevenue")),
    }
    diagnosis = {
        "traffic_label": "Traffic measured" if source_status["ga4"] else "Waiting for GA4 traffic",
        "visibility_label": "Search demand measured" if source_status["gsc"] else "Waiting for GSC impressions",
        "revenue_label": "Revenue-linked" if source_status["ecommerce"] else "Not connected",
    }

    return {
        "ok": True,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "target_scope": target_scope,
        "period": current,
        "previous_period": previous,
        "gsc": {
            "site_url": gsc_site_url,
            "summary": gsc_current,
            "previous": gsc_previous,
            "trends": {
                "clicks": percent_change(gsc_current.get("clicks"), gsc_previous.get("clicks")),
                "impressions": percent_change(gsc_current.get("impressions"), gsc_previous.get("impressions")),
                "ctr": percent_change(gsc_current.get("ctr"), gsc_previous.get("ctr")),
                "position": percent_change(gsc_previous.get("position"), gsc_current.get("position")),
            },
            "top_queries": gsc_queries,
            "top_pages": gsc_pages,
        },
        "ga4": {
            "property_id": ga4_property_id,
            "summary": ga4_current,
            "previous": ga4_previous,
            "trends": {key: percent_change(ga4_current.get(key), ga4_previous.get(key)) for key in core_metrics},
            "channel_groups": channel_groups if isinstance(channel_groups, list) else [],
            "landing_pages": landing_pages if isinstance(landing_pages, list) else [],
            "events": events if isinstance(events, list) else [],
            "ecommerce": ecommerce_metrics,
            "report_errors": ga4_errors,
        },
        "scorecard": {
            "period_label": f"{current['start_date']} to {current['end_date']}",
            "source_status": source_status,
            "metrics": {
                "organic_sessions": organic_sessions(channel_groups if isinstance(channel_groups, list) else []),
                "revenue": safe_float(ecommerce_metrics.get("purchaseRevenue")),
                "orders": safe_float(ecommerce_metrics.get("ecommercePurchases")),
                "channel_mix": channels,
            },
            "diagnosis": diagnosis,
        },
        "opportunities": opportunities,
    }


def demo_report() -> dict[str, Any]:
    queries = [
        {"query": "best crm software for agencies", "clicks": 18, "impressions": 1800, "ctr": 0.01, "position": 6.4},
        {"query": "marketing dashboard template", "clicks": 5, "impressions": 900, "ctr": 0.0055, "position": 9.8},
        {"query": "seo reporting tool", "clicks": 42, "impressions": 1250, "ctr": 0.0336, "position": 3.2},
        {"query": "google search console dashboard", "clicks": 0, "impressions": 240, "ctr": 0, "position": 14.1},
    ]
    pages = [
        {"page": "https://example.com/blog/search-console-dashboard", "clicks": 34, "impressions": 3100, "ctr": 0.011, "position": 7.1},
        {"page": "https://example.com/templates/seo-report", "clicks": 12, "impressions": 880, "ctr": 0.0136, "position": 11.5},
    ]
    current = {"start_date": "2026-04-19", "end_date": "2026-05-18"}
    return {
        "ok": True,
        "demo": True,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "target_scope": {"label": "Site-wide", "mode": "site", "url": "https://example.com/"},
        "period": current,
        "gsc": {
            "site_url": "https://example.com/",
            "summary": {"clicks": 423, "impressions": 38200, "ctr": 0.0111, "position": 8.7},
            "trends": {"clicks": 12.4, "impressions": 19.8, "ctr": -6.2, "position": 3.4},
            "top_queries": queries,
            "top_pages": pages,
        },
        "ga4": {
            "property_id": "demo",
            "summary": {"sessions": 9200, "totalUsers": 6100, "screenPageViews": 18400, "engagedSessions": 5300},
            "channel_groups": [
                {"dimensions": {"sessionDefaultChannelGroup": "Organic Search"}, "metrics": {"sessions": 4200, "totalUsers": 3300, "engagedSessions": 2600}},
                {"dimensions": {"sessionDefaultChannelGroup": "Direct"}, "metrics": {"sessions": 2100, "totalUsers": 1500, "engagedSessions": 1100}},
                {"dimensions": {"sessionDefaultChannelGroup": "Referral"}, "metrics": {"sessions": 760, "totalUsers": 520, "engagedSessions": 410}},
                {"dimensions": {"sessionDefaultChannelGroup": "Organic Social"}, "metrics": {"sessions": 540, "totalUsers": 460, "engagedSessions": 250}},
            ],
            "landing_pages": [
                {"dimensions": {"landingPagePlusQueryString": "/blog/search-console-dashboard"}, "metrics": {"sessions": 1700, "screenPageViews": 4200, "engagedSessions": 980}},
                {"dimensions": {"landingPagePlusQueryString": "/templates/seo-report"}, "metrics": {"sessions": 980, "screenPageViews": 2200, "engagedSessions": 620}},
            ],
            "events": [],
            "ecommerce": {"ecommercePurchases": 18, "purchaseRevenue": 3280},
        },
        "scorecard": {
            "period_label": f"{current['start_date']} to {current['end_date']}",
            "source_status": {"gsc": True, "ga4": True, "ecommerce": True},
            "metrics": {
                "organic_sessions": 4200,
                "orders": 18,
                "revenue": 3280,
                "channel_mix": {"organic": 0.456, "direct": 0.228, "referral": 0.083, "social": 0.059, "total": 9200},
            },
            "diagnosis": {"traffic_label": "Traffic measured", "visibility_label": "Search demand measured", "revenue_label": "Revenue-linked"},
        },
        "opportunities": opportunity_engine(queries, pages, min_impressions=20),
    }
