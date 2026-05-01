"""Optional Streamlit renderer for the Phase2-4 read-only preview model.

This module keeps Streamlit isolated from core service/runtime imports.  The
renderer accepts an already-built preview model for tests and future adapters;
the script entrypoint imports Streamlit only when explicitly invoked.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from src.common.config import AppConfig
from src.common.errors import ConfigError
from src.common.files import load_json
from src.marts.builder import build_mart_from_fixture
from src.service.preview_adapter import build_phase2_4_preview_model


def render_phase2_4_streamlit_preview(preview_model: dict[str, Any], streamlit: Any) -> None:
    """Render the preview model with a Streamlit-compatible object."""

    streamlit.set_page_config(page_title="APO Phase2-4 Preview", layout="wide")
    streamlit.title("APO Phase2-4 Read-Only Preview")
    streamlit.caption("Streamlit preview surface; production dashboard framework remains unfrozen.")

    guardrails = preview_model["cutover_guardrails"]
    columns = streamlit.columns(3)
    columns[0].metric("cutover_eligible", str(guardrails["cutover_eligible"]).lower())
    columns[1].metric("runtime_cutover_executed", str(guardrails["runtime_cutover_executed"]).lower())
    columns[2].metric("production_db_readiness_claimed", str(guardrails["production_db_readiness_claimed"]).lower())

    overview_tab, trace_tab, review_tab, task_tab, contract_tab = streamlit.tabs(
        ["Overview", "Product Trace", "Review Queue", "Task Inspection", "Contract"]
    )
    service_reads = preview_model["service_reads"]

    with overview_tab:
        streamlit.subheader("Overview")
        streamlit.json(
            {
                "framework_policy": preview_model["framework_policy"],
                "dashboard_mart_view": service_reads["dashboard_mart_view"],
            }
        )
    with trace_tab:
        streamlit.subheader("Product Trace")
        streamlit.json(service_reads["product_drill_down"] or {"selected_product_id": None})
    with review_tab:
        streamlit.subheader("Review Queue")
        streamlit.json(service_reads["review_queue_view"])
    with task_tab:
        streamlit.subheader("Task Inspection")
        streamlit.json(service_reads["task_inspection_view"])
    with contract_tab:
        streamlit.subheader("Read Contract")
        streamlit.json(
            {
                "navigation": preview_model["navigation"],
                "blocked_actions": preview_model["blocked_actions"],
                "operator_api_contract": service_reads["operator_api_contract"],
            }
        )


def run_phase2_4_streamlit_preview(
    *,
    mart_path: str | None = None,
    product_id: str | None = None,
    open_review_only: bool = False,
    task_id: str | None = None,
    task_status: str | None = None,
    request_id: str | None = None,
) -> None:
    """Explicit Streamlit entrypoint; importing this module stays dependency-light."""

    streamlit = _import_streamlit()
    config = AppConfig.from_env(Path.cwd())
    mart = _load_or_read_mart(config, mart_path)
    preview_model = build_phase2_4_preview_model(
        config=config,
        mart=mart,
        product_id=product_id,
        open_review_only=open_review_only,
        task_id=task_id,
        task_status=task_status,
        request_id=request_id,
    )
    render_phase2_4_streamlit_preview(preview_model, streamlit)


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit preview-only Streamlit entrypoint parser."""

    parser = argparse.ArgumentParser(
        prog="python3 -m src.frontend.streamlit_preview",
        description="Run the optional Phase2-4 Streamlit read-only preview surface.",
    )
    parser.add_argument("--mart-path")
    parser.add_argument("--product-id")
    parser.add_argument("--open-review-only", action="store_true")
    parser.add_argument("--task-id")
    parser.add_argument("--task-status")
    parser.add_argument("--request-id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse preview-only args and render the optional Streamlit surface."""

    args = build_parser().parse_args(argv)
    try:
        run_phase2_4_streamlit_preview(
            mart_path=args.mart_path,
            product_id=args.product_id,
            open_review_only=args.open_review_only,
            task_id=args.task_id,
            task_status=args.task_status,
            request_id=args.request_id,
        )
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _load_or_read_mart(config: AppConfig, mart_path: str | None) -> dict[str, Any]:
    if mart_path:
        path = Path(mart_path)
        if not path.exists():
            raise ConfigError(f"Mart path does not exist: {path}")
        payload = load_json(path)
        if not isinstance(payload, dict):
            raise ConfigError(f"Mart path must contain a JSON object: {path}")
        return payload
    return build_mart_from_fixture(
        config.fixtures_dir / "marts" / "effective_results_window.json",
        config.config_dir / "source_registry.yaml",
    )


def _import_streamlit() -> Any:
    try:
        import streamlit
    except ModuleNotFoundError as exc:
        raise ConfigError(
            "Streamlit is not installed; install it only for the optional Phase2-4 read-only preview surface."
        ) from exc
    return streamlit


if __name__ == "__main__":
    raise SystemExit(main())
