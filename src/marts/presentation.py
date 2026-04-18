"""Presentation-layer readers for the Phase1-F/Phase1-G local mart baseline."""

from __future__ import annotations

from typing import Any


def build_dashboard_view(mart: dict[str, Any]) -> dict[str, Any]:
    """Build dashboard cards from the mart artifact without rejoining runtime tables."""

    contract = mart.get("dashboard_read_contract") or {}
    return {
        "main_report_dataset": contract.get("main_report_dataset"),
        "main_report_semantics": contract.get("main_report_semantics"),
        "cards": {
            "top_jtbd_products_30d": list(mart.get("top_jtbd_products_30d") or []),
            "attention_distribution_30d": list(mart.get("attention_distribution_30d") or []),
            "unresolved_backlog": {
                "open_item_count": len(mart.get("unresolved_registry_view") or []),
                "items": list(mart.get("unresolved_registry_view") or []),
            },
        },
    }


def build_product_drill_down(mart: dict[str, Any], *, product_id: str) -> dict[str, Any]:
    """Return the mart-backed drill-down payload for one product."""

    product = _index_by(mart.get("dim_product") or [], "product_id").get(product_id)
    trace = _index_by(mart.get("drill_down_trace") or [], "product_id").get(product_id)
    fact_rows = [row for row in (mart.get("fact_product_observation") or []) if row.get("product_id") == product_id]
    unresolved_entry = _index_by(mart.get("unresolved_registry_view") or [], "target_id").get(product_id)

    if product is None or trace is None:
        raise KeyError(f"Product is not present in mart drill-down trace: {product_id}")

    return {
        "product": product,
        "main_report_included": trace["main_report_included"],
        "effective_taxonomy_code": trace.get("effective_taxonomy_code"),
        "fact_rows": fact_rows,
        "trace_refs": {
            "source_item_id": trace.get("source_item_id"),
            "observation_id": trace.get("observation_id"),
            "evidence_ids": list(trace.get("evidence_ids") or []),
            "review_issue_ids": list(trace.get("review_issue_ids") or []),
        },
        "unresolved_registry_entry": unresolved_entry,
    }


def reconcile_dashboard_view(mart: dict[str, Any]) -> dict[str, Any]:
    """Compare dashboard-facing reads with the mart contract they must mirror."""

    dashboard = build_dashboard_view(mart)
    contract = mart.get("dashboard_read_contract") or {}
    unresolved_items = list(mart.get("unresolved_registry_view") or [])
    checks = [
        _check(
            "main_report_dataset",
            dashboard.get("main_report_dataset"),
            contract.get("main_report_dataset"),
        ),
        _check(
            "main_report_semantics",
            dashboard.get("main_report_semantics"),
            contract.get("main_report_semantics"),
        ),
        _check(
            "top_jtbd_products_30d",
            dashboard.get("cards", {}).get("top_jtbd_products_30d"),
            list(mart.get("top_jtbd_products_30d") or []),
        ),
        _check(
            "attention_distribution_30d",
            dashboard.get("cards", {}).get("attention_distribution_30d"),
            list(mart.get("attention_distribution_30d") or []),
        ),
        _check(
            "unresolved_backlog_open_item_count",
            dashboard.get("cards", {}).get("unresolved_backlog", {}).get("open_item_count"),
            len(unresolved_items),
        ),
        _check(
            "unresolved_backlog_items",
            dashboard.get("cards", {}).get("unresolved_backlog", {}).get("items"),
            unresolved_items,
        ),
    ]
    passed_count = sum(1 for check in checks if check["passed"])
    check_count = len(checks)
    return {
        "window_start": mart.get("window_start"),
        "window_end": mart.get("window_end"),
        "mart_version": mart.get("mart_version"),
        "dashboard_contract_ref": {
            "main_report_dataset": contract.get("main_report_dataset"),
            "main_report_semantics": contract.get("main_report_semantics"),
            "runtime_detail_join_allowed": contract.get("runtime_detail_join_allowed"),
        },
        "check_count": check_count,
        "passed_count": passed_count,
        "pass_rate": passed_count / check_count if check_count else 0.0,
        "all_passed": passed_count == check_count,
        "checks": checks,
    }


def _index_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {
        row[key]: row
        for row in rows
        if isinstance(row, dict) and row.get(key) is not None
    }


def _check(check_id: str, actual: object, expected: object) -> dict[str, object]:
    return {
        "check_id": check_id,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }
