from __future__ import annotations

import unittest

from src.classification.taxonomy_classifier import classify_product
from src.extractors.evidence_extractor import extract_evidence
from src.profiling.product_profiler import build_product_profile
from src.resolution.entity_resolver import resolve_source_item
from src.resolution.observation_builder import build_observation
from src.scoring.score_engine import score_product
from tests.helpers import REPO_ROOT


class Phase1DerivationIntegrationTests(unittest.TestCase):
    def test_source_item_to_profile_taxonomy_and_score_chain(self) -> None:
        source_item = {
            "source_item_id": "src_item_integration_1",
            "raw_id": "raw_integration_1",
            "source_id": "src_product_hunt",
            "external_id": "ph_integration_1",
            "canonical_url": "https://example.com/research-agent",
            "linked_homepage_url": "https://example.com/research-agent",
            "linked_repo_url": None,
            "title": "Research Agent",
            "author_name": "Acme",
            "published_at": "2026-03-01T00:00:00Z",
            "raw_text_excerpt": (
                "Built with GPT workflows in a weekend. A web app for researchers to search internal docs, "
                "answer questions, and summarize reports. Pricing starts at $29."
            ),
            "current_summary": "Web app for researchers to search docs and answer questions with traceable evidence.",
            "current_metrics_json": {"vote_count": 52},
            "first_observed_at": "2026-03-01T00:00:00Z",
            "latest_observed_at": "2026-03-01T00:00:00Z",
            "normalization_version": "product_hunt_v1",
        }

        product = resolve_source_item(source_item)["product"]
        observation = build_observation(product, source_item)
        evidence = extract_evidence(source_item, product_id=product["product_id"])
        profile = build_product_profile(
            product,
            source_item,
            evidence,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
        )
        assignment = classify_product(
            profile,
            evidence,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
        )[0]
        benchmark = [
            {"source_id": "src_product_hunt", "relation_type": "launch", "metrics_snapshot": {"vote_count": value}}
            for value in range(10, 80)
        ]
        scores = score_product(
            product,
            profile,
            evidence,
            observation,
            source_item,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
            benchmark_observations=benchmark,
        )

        self.assertEqual(observation["product_id"], product["product_id"])
        self.assertTrue(all(item["source_item_id"] == source_item["source_item_id"] for item in evidence))
        self.assertEqual(profile["product_id"], product["product_id"])
        self.assertEqual(assignment["target_id"], product["product_id"])
        self.assertEqual(assignment["category_code"], "JTBD_KNOWLEDGE")
        components = {component["score_type"]: component for component in scores["score_components"]}
        self.assertEqual(components["build_evidence_score"]["band"], "high")
        self.assertEqual(components["need_clarity_score"]["band"], "high")
        self.assertEqual(components["commercial_score"]["band"], "high")


if __name__ == "__main__":
    unittest.main()
