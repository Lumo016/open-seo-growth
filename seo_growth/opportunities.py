from __future__ import annotations

from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def percent_change(current: Any, previous: Any) -> float | None:
    current_value = safe_float(current)
    previous_value = safe_float(previous)
    if previous_value == 0:
        return None
    return ((current_value - previous_value) / previous_value) * 100


def expected_ctr_for_position(position: Any) -> float:
    pos = safe_float(position)
    if pos <= 0:
        return 0.0
    if pos <= 1.5:
        return 0.28
    if pos <= 2.5:
        return 0.15
    if pos <= 3.5:
        return 0.10
    if pos <= 5:
        return 0.065
    if pos <= 10:
        return 0.035
    if pos <= 20:
        return 0.014
    return 0.006


def enrich_opportunity(row: dict[str, Any], label_key: str) -> dict[str, Any]:
    impressions = safe_float(row.get("impressions"))
    clicks = safe_float(row.get("clicks"))
    position = safe_float(row.get("position"))
    ctr = safe_float(row.get("ctr"))
    expected_ctr = expected_ctr_for_position(position)
    missed_clicks = max(0.0, (expected_ctr - ctr) * impressions)
    rank_gap = max(0.0, min(position - 3, 12))
    opportunity_score = round((missed_clicks * 4) + (impressions / 25) + (rank_gap * 3), 1)
    return {
        **row,
        "label": row.get(label_key) or "-",
        "expected_ctr": expected_ctr,
        "missed_clicks": round(missed_clicks, 1),
        "opportunity_score": opportunity_score,
    }


def rank_buckets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = [
        {"id": "top3", "label": "Top 3", "min": 0, "max": 3},
        {"id": "first_page", "label": "Positions 4-10", "min": 3, "max": 10},
        {"id": "second_page", "label": "Positions 11-20", "min": 10, "max": 20},
        {"id": "discovery", "label": "21+", "min": 20, "max": 999},
    ]
    total_impressions = sum(safe_float(row.get("impressions")) for row in rows)
    output: list[dict[str, Any]] = []
    for bucket in buckets:
        bucket_rows = [
            row for row in rows
            if bucket["min"] < safe_float(row.get("position")) <= bucket["max"]
        ]
        impressions = sum(safe_float(row.get("impressions")) for row in bucket_rows)
        clicks = sum(safe_float(row.get("clicks")) for row in bucket_rows)
        output.append(
            {
                "id": bucket["id"],
                "label": bucket["label"],
                "query_count": len(bucket_rows),
                "clicks": clicks,
                "impressions": impressions,
                "share": impressions / total_impressions if total_impressions else 0,
            }
        )
    return output


def opportunity_engine(
    queries: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    *,
    min_impressions: int,
) -> dict[str, Any]:
    enriched_queries = [enrich_opportunity(row, "query") for row in queries]
    enriched_pages = [enrich_opportunity(row, "page") for row in pages]
    low_hanging = [
        row
        for row in enriched_queries
        if row["impressions"] >= min_impressions and 4 <= row["position"] <= 15
    ]
    ctr_opportunities = [
        row
        for row in enriched_queries
        if row["impressions"] >= min_impressions
        and row["position"] <= 10
        and row["expected_ctr"] > 0
        and row["ctr"] < row["expected_ctr"] * 0.65
    ]
    page_opportunities = [
        row
        for row in enriched_pages
        if row["impressions"] >= min_impressions and 4 <= row["position"] <= 20
    ]
    return {
        "min_impressions": min_impressions,
        "low_hanging_queries": sorted(low_hanging, key=lambda item: item["opportunity_score"], reverse=True)[:12],
        "ctr_opportunities": sorted(ctr_opportunities, key=lambda item: item["missed_clicks"], reverse=True)[:12],
        "page_opportunities": sorted(page_opportunities, key=lambda item: item["opportunity_score"], reverse=True)[:10],
        "rank_buckets": rank_buckets(queries),
        "method": "GSC impressions + average position + heuristic CTR gap",
    }

