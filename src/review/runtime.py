"""Runtime helpers that connect Phase1-D taxonomy outputs to the local review control plane."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.classification.taxonomy_classifier import classify_product
from src.common.errors import ContractValidationError
from src.common.files import dump_json, load_json
from src.extractors.evidence_extractor import extract_evidence
from src.profiling.product_profiler import build_product_profile
from src.resolution.entity_resolver import resolve_source_item
from src.review.review_packet_builder import build_review_issue_artifacts
from src.review.store import (
    FileReviewIssueStore,
    default_review_issue_store_path,
    open_taxonomy_review_record,
    resolve_taxonomy_review_record,
)


def classify_product_with_review(
    product: dict[str, Any],
    source_item: dict[str, Any],
    product_profile: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    config_dir: Path,
    schema_dir: Path,
    task_store_path: Path,
    assigned_at: str | None = None,
    issue_type: str | None = None,
    priority_code: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    assignments = classify_product(
        product_profile,
        evidence,
        config_dir=config_dir,
        schema_dir=schema_dir,
        assigned_at=assigned_at,
    )
    record = _build_taxonomy_record(product, source_item, assignments)
    result: dict[str, Any] = {
        "taxonomy_assignments": assignments,
        "record": record,
        "review_triggered": False,
        "review_issue": None,
        "review_queue_view": None,
    }
    if not _should_trigger_taxonomy_review(assignments[0]):
        return result

    store = FileReviewIssueStore(default_review_issue_store_path(task_store_path))
    opened = open_taxonomy_review_record(
        record,
        store=store,
        target_summary=_taxonomy_target_summary(product, assignments[0]),
        upstream_downstream_links=_taxonomy_links(product, source_item, assignments[0]),
        config_dir=config_dir,
        schema_dir=schema_dir,
        issue_type=issue_type,
        priority_code=priority_code,
        created_at=created_at or assignments[0]["assigned_at"],
        related_evidence=_related_evidence(evidence),
    )
    result.update(
        {
            "record": opened["record"],
            "review_triggered": True,
            "review_issue": opened["review_issue"],
            "review_queue_view": opened["review_queue_view"],
        }
    )
    return result


def trigger_taxonomy_review_from_source_item(
    source_item: dict[str, Any],
    *,
    config_dir: Path,
    schema_dir: Path,
    task_store_path: Path,
    record_path: Path | None = None,
    issue_type: str | None = None,
    priority_code: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    resolution = resolve_source_item(source_item)
    product = resolution.get("product")
    if product is None:
        raise ContractValidationError(
            "trigger-taxonomy-review only supports source items that already resolve to a single product; "
            "entity_merge_uncertainty remains a separate review path."
        )

    evidence = extract_evidence(source_item, product_id=product["product_id"])
    profile = build_product_profile(
        product,
        source_item,
        evidence,
        config_dir=config_dir,
        schema_dir=schema_dir,
    )
    routed = classify_product_with_review(
        product,
        source_item,
        profile,
        evidence,
        config_dir=config_dir,
        schema_dir=schema_dir,
        task_store_path=task_store_path,
        issue_type=issue_type,
        priority_code=priority_code,
        created_at=created_at,
    )
    output_path = record_path.resolve() if record_path else None
    if output_path is not None:
        dump_json(output_path, routed["record"])

    assignment = routed["taxonomy_assignments"][0]
    review_issue = routed.get("review_issue")
    return {
        "product_id": product["product_id"],
        "category_code": assignment["category_code"],
        "confidence": assignment.get("confidence"),
        "review_triggered": routed["review_triggered"],
        "review_issue_id": review_issue["review_issue_id"] if isinstance(review_issue, dict) else None,
        "record_path": str(output_path) if output_path is not None else None,
    }


def list_review_queue(*, config_dir: Path, task_store_path: Path, open_only: bool = False) -> list[dict[str, Any]]:
    store = FileReviewIssueStore(default_review_issue_store_path(task_store_path))
    return store.queue_entries(config_dir=config_dir, open_only=open_only)


def trigger_entity_review_from_source_item(
    source_item: dict[str, Any],
    *,
    existing_products: list[dict[str, Any]],
    config_dir: Path,
    schema_dir: Path,
    task_store_path: Path,
    priority_code: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    resolution = resolve_source_item(source_item, existing_products=existing_products)
    candidate = resolution.get("entity_match_candidate")
    if not isinstance(candidate, dict):
        return {
            "review_triggered": False,
            "issue_type": None,
            "review_issue_id": None,
            "candidate_id": None,
        }

    store = FileReviewIssueStore(default_review_issue_store_path(task_store_path))
    artifacts = build_review_issue_artifacts(
        target_type="product",
        target_id=source_item.get("external_id") or source_item["source_item_id"],
        target_summary=f"Entity merge uncertainty for source item {source_item['source_item_id']}.",
        issue_type="entity_merge_uncertainty",
        current_auto_result={
            "candidate_id": candidate["candidate_id"],
            "matched_product_ids": (candidate.get("candidate_features_json") or {}).get("matched_product_ids") or [],
            "suggested_action": candidate.get("suggested_action"),
            "confidence": candidate.get("confidence"),
        },
        related_evidence=[
            {
                "source_item_id": source_item["source_item_id"],
                "evidence_type": "entity_match_candidate",
                "source_url": source_item.get("canonical_url") or source_item.get("linked_homepage_url"),
            }
        ],
        conflict_point="Multiple existing products matched the same source item, so merge cannot become effective without review.",
        recommended_action="needs_more_evidence",
        upstream_downstream_links=[
            {
                "source_item_id": source_item["source_item_id"],
                "candidate_id": candidate["candidate_id"],
            }
        ],
        config_dir=config_dir,
        schema_dir=schema_dir,
        priority_code=priority_code,
        created_at=created_at or candidate.get("created_at"),
    )
    stored_issue = store.upsert(artifacts["review_issue"])
    return {
        "review_triggered": True,
        "issue_type": stored_issue["issue_type"],
        "review_issue_id": stored_issue["review_issue_id"],
        "candidate_id": candidate["candidate_id"],
        "review_queue_view": artifacts["review_queue_view"],
    }


def trigger_score_review_from_snapshot(
    score_snapshot: dict[str, Any],
    *,
    issue_type: str,
    config_dir: Path,
    schema_dir: Path,
    task_store_path: Path,
    priority_code: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    if issue_type not in {"score_conflict", "suspicious_result"}:
        raise ContractValidationError("Score review triggers only support score_conflict or suspicious_result")
    target_id = str(score_snapshot.get("target_id") or score_snapshot.get("product_id") or "")
    if not target_id:
        raise ContractValidationError("score_snapshot must include product_id or target_id")

    current_auto_result = _score_current_auto_result(score_snapshot)
    source_item_id = score_snapshot.get("source_item_id")
    source_url = score_snapshot.get("source_url")
    if not source_item_id or not source_url:
        raise ContractValidationError("score_snapshot must include source_item_id and source_url for traceable review evidence")

    store = FileReviewIssueStore(default_review_issue_store_path(task_store_path))
    artifacts = build_review_issue_artifacts(
        target_type="product",
        target_id=target_id,
        target_summary=f"Score review required for {target_id}.",
        issue_type=issue_type,
        current_auto_result=current_auto_result,
        related_evidence=[
            {
                "source_item_id": source_item_id,
                "evidence_type": "score_component_trace",
                "source_url": source_url,
            }
        ],
        conflict_point=str(score_snapshot.get("conflict_point") or "Score output requires human review before it can be trusted."),
        recommended_action=str(score_snapshot.get("recommended_action") or "needs_more_evidence"),
        upstream_downstream_links=_score_links(score_snapshot),
        config_dir=config_dir,
        schema_dir=schema_dir,
        priority_code=priority_code,
        created_at=created_at or score_snapshot.get("computed_at"),
    )
    stored_issue = store.upsert(artifacts["review_issue"])
    return {
        "review_triggered": True,
        "issue_type": stored_issue["issue_type"],
        "review_issue_id": stored_issue["review_issue_id"],
        "review_queue_view": artifacts["review_queue_view"],
    }


def resolve_taxonomy_review_from_record_path(
    record_path: Path,
    *,
    config_dir: Path,
    schema_dir: Path,
    task_store_path: Path,
    review_issue_id: str,
    resolution_action: str,
    resolution_notes: str,
    reviewer: str,
    reviewed_at: str | None = None,
    approver: str | None = None,
    approved_at: str | None = None,
    override_category_code: str | None = None,
    unresolved_mode: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    record = _require_record(load_json(record_path), record_path)
    store = FileReviewIssueStore(default_review_issue_store_path(task_store_path))
    resolved = resolve_taxonomy_review_record(
        record,
        store=store,
        review_issue_id=review_issue_id,
        target_summary=_target_summary_from_record(record),
        upstream_downstream_links=_links_from_record(record),
        resolution_action=resolution_action,
        resolution_notes=resolution_notes,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        approver=approver,
        approved_at=approved_at,
        override_category_code=override_category_code,
        unresolved_mode=unresolved_mode,
        config_dir=config_dir,
        schema_dir=schema_dir,
    )
    destination = (output_path or record_path).resolve()
    dump_json(destination, resolved["record"])
    return {
        "review_issue_id": resolved["review_issue"]["review_issue_id"],
        "status": resolved["review_issue"]["status"],
        "resolution_action": resolved["review_issue"]["resolution_action"],
        "maker_checker_required": resolved["review_issue"]["maker_checker_required"],
        "output_path": str(destination),
        "effective_category_code": (resolved["record"].get("effective_taxonomy") or {}).get("category_code"),
    }


def _should_trigger_taxonomy_review(assignment: dict[str, Any]) -> bool:
    if assignment.get("category_code") == "unresolved":
        return True
    confidence = assignment.get("confidence")
    return confidence is None or float(confidence) < 0.75


def _build_taxonomy_record(
    product: dict[str, Any],
    source_item: dict[str, Any],
    assignments: list[dict[str, Any]],
) -> dict[str, Any]:
    source_item_id = source_item["source_item_id"]
    return {
        "product_id": product["product_id"],
        "source_id": source_item["source_id"],
        "source_item_id": source_item_id,
        "source_url": source_item.get("canonical_url") or source_item.get("linked_homepage_url"),
        "taxonomy_assignments": [dict(item) for item in assignments],
        "review_issues": [],
        "drill_down_refs": {
            "product_id": product["product_id"],
            "source_item_id": source_item_id,
            "review_issue_ids": [],
        },
        "effective_taxonomy": dict(assignments[0]),
    }


def _taxonomy_target_summary(product: dict[str, Any], assignment: dict[str, Any]) -> str:
    return (
        f"Taxonomy review required for {product['product_id']}: "
        f"classifier produced {assignment['category_code']} at confidence {assignment.get('confidence')}."
    )


def _taxonomy_links(product: dict[str, Any], source_item: dict[str, Any], assignment: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "product_id": product["product_id"],
            "source_item_id": source_item["source_item_id"],
            "source_id": source_item["source_id"],
            "taxonomy_version": assignment["taxonomy_version"],
            "model_or_rule_version": assignment["model_or_rule_version"],
        }
    ]


def _related_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in evidence:
        ref = {
            "source_item_id": item["source_item_id"],
            "evidence_type": item["evidence_type"],
            "source_url": item["source_url"],
        }
        refs.append(ref)
        if len(refs) == 3:
            break
    return refs


def _require_record(payload: object, record_path: Path) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractValidationError(f"Taxonomy review record must be a JSON object: {record_path}")
    return payload


def _target_summary_from_record(record: dict[str, Any]) -> str:
    product_id = record.get("product_id") or "unknown_product"
    return f"Resolve taxonomy review for {product_id}."


def _links_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    links = {
        "product_id": record.get("product_id"),
        "source_item_id": record.get("source_item_id"),
        "source_id": record.get("source_id"),
    }
    return [{key: value for key, value in links.items() if value}]


def _score_current_auto_result(score_snapshot: dict[str, Any]) -> dict[str, Any]:
    current = score_snapshot.get("current_auto_result")
    if isinstance(current, dict) and current:
        return current
    components = score_snapshot.get("score_components")
    if isinstance(components, list) and components:
        component = components[0]
        if isinstance(component, dict) and component:
            return {
                "score_type": component.get("score_type"),
                "band": component.get("band"),
                "normalized_value": component.get("normalized_value"),
                "rationale": component.get("rationale"),
            }
    raise ContractValidationError("score_snapshot must include current_auto_result or score_components")


def _score_links(score_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    links = {
        "product_id": score_snapshot.get("target_id") or score_snapshot.get("product_id"),
        "score_run_id": score_snapshot.get("score_run_id"),
        "source_item_id": score_snapshot.get("source_item_id"),
    }
    return [{key: value for key, value in links.items() if value}]
