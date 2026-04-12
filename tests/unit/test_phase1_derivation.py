from __future__ import annotations

import unittest

from src.classification.taxonomy_classifier import classify_product
from src.extractors.evidence_extractor import extract_evidence
from src.profiling.product_profiler import build_product_profile
from src.resolution.entity_resolver import resolve_source_item
from src.resolution.observation_builder import build_observation
from src.scoring.score_engine import score_product
from tests.helpers import REPO_ROOT


class Phase1DerivationTests(unittest.TestCase):
    def test_phase1_d_chain_produces_traceable_outputs(self) -> None:
        source_item = {
            "source_item_id": "src_item_knowledge_1",
            "raw_id": "raw_knowledge_1",
            "source_id": "src_product_hunt",
            "external_id": "ph_knowledge_1",
            "canonical_url": "https://example.com/desk-research-copilot",
            "linked_homepage_url": "https://example.com/desk-research-copilot",
            "linked_repo_url": None,
            "title": "Desk Research Copilot",
            "author_name": "Acme",
            "published_at": "2026-03-01T00:00:00Z",
            "raw_text_excerpt": (
                "Built with Claude in a weekend. A web app for researchers and support teams "
                "to search internal docs, answer questions, and summarize findings. Pricing starts at $49."
            ),
            "current_summary": "A web app that helps researchers search internal docs and answer questions fast.",
            "current_metrics_json": {"vote_count": 88},
            "first_observed_at": "2026-03-01T00:00:00Z",
            "latest_observed_at": "2026-03-01T00:00:00Z",
            "normalization_version": "product_hunt_v1",
        }

        resolution = resolve_source_item(source_item)
        product = resolution["product"]
        self.assertIsNotNone(product)
        self.assertIsNone(resolution["entity_match_candidate"])

        observation = build_observation(product, source_item)
        evidence = extract_evidence(source_item, product_id=product["product_id"])
        profile = build_product_profile(
            product,
            source_item,
            evidence,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
        )
        assignments = classify_product(
            profile,
            evidence,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
        )
        benchmark = [
            {"source_id": "src_product_hunt", "relation_type": "launch", "metrics_snapshot": {"vote_count": value}}
            for value in range(30, 90)
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

        self.assertEqual(observation["relation_type"], "launch")
        self.assertGreaterEqual(len(evidence), 4)
        self.assertEqual(profile["primary_persona_code"], "support_agent")
        self.assertEqual(profile["delivery_form_code"], "web_app")
        self.assertEqual(assignments[0]["category_code"], "JTBD_KNOWLEDGE")
        components = {component["score_type"]: component for component in scores["score_components"]}
        self.assertEqual(components["build_evidence_score"]["band"], "high")
        self.assertEqual(components["need_clarity_score"]["band"], "high")
        self.assertIsNotNone(components["attention_score"]["normalized_value"])
        self.assertIn("source_item_id", components["build_evidence_score"]["evidence_refs_json"][0])

    def test_taxonomy_classifier_routes_ambiguous_case_to_unresolved(self) -> None:
        profile = {
            "product_id": "prod_ambiguous",
            "profile_version": "product_profiler_v1",
            "one_sentence_job": "General AI assistant for any writing or research task.",
            "primary_persona_code": "unknown",
            "delivery_form_code": "chat_assistant",
            "summary": "General AI assistant for any writing or research task.",
            "evidence_refs_json": [{"source_item_id": "src_item_1", "evidence_type": "job_statement"}],
            "extracted_at": "2026-03-01T00:00:00Z",
            "extracted_by": "product_profiler_v1",
        }
        evidence = [
            {
                "source_item_id": "src_item_1",
                "product_id": "prod_ambiguous",
                "evidence_type": "job_statement",
                "snippet": "General AI assistant for any writing or research task.",
                "source_url": "https://example.com/ambiguous",
                "evidence_strength": "medium",
                "parser_or_model_version": "evidence_extractor_v1",
                "extracted_at": "2026-03-01T00:00:00Z",
            },
            {
                "source_item_id": "src_item_1",
                "product_id": "prod_ambiguous",
                "evidence_type": "unclear_description_signal",
                "snippet": "General AI assistant for everyone.",
                "source_url": "https://example.com/ambiguous",
                "evidence_strength": "low",
                "parser_or_model_version": "evidence_extractor_v1",
                "extracted_at": "2026-03-01T00:00:00Z",
            },
        ]

        assignments = classify_product(
            profile,
            evidence,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
        )
        self.assertEqual(assignments[0]["category_code"], "unresolved")

    def test_attention_score_keeps_raw_value_and_null_band_when_sample_is_insufficient(self) -> None:
        source_item = {
            "source_item_id": "src_item_attention_1",
            "raw_id": "raw_attention_1",
            "source_id": "src_github",
            "external_id": "gh_attention_1",
            "canonical_url": "https://github.com/acme/support-agent-workbench",
            "linked_homepage_url": "https://acme.example.com",
            "linked_repo_url": "https://github.com/acme/support-agent-workbench",
            "title": "support-agent-workbench",
            "author_name": "Acme",
            "published_at": "2026-03-01T00:00:00Z",
            "raw_text_excerpt": "Developer tool to debug support workflows.",
            "current_summary": "Developer tool to debug support workflows.",
            "current_metrics_json": {"star_count": 144},
            "first_observed_at": "2026-03-01T00:00:00Z",
            "latest_observed_at": "2026-03-01T00:00:00Z",
            "normalization_version": "github_v1",
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

        scored = score_product(
            product,
            profile,
            evidence,
            observation,
            source_item,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
            benchmark_observations=[{"source_id": "src_github", "relation_type": "repo", "metrics_snapshot": {"star_count": 12}}],
        )
        attention = next(component for component in scored["score_components"] if component["score_type"] == "attention_score")
        self.assertEqual(attention["raw_value"], 144)
        self.assertIsNone(attention["normalized_value"])
        self.assertIsNone(attention["band"])
        self.assertEqual(attention["rationale"], "benchmark_sample_insufficient")

    def test_entity_resolver_opens_candidate_when_multiple_products_match(self) -> None:
        source_item = {
            "source_item_id": "src_item_collision_1",
            "raw_id": "raw_collision_1",
            "source_id": "src_product_hunt",
            "external_id": "ph_collision_1",
            "canonical_url": "https://example.com/copilot",
            "linked_homepage_url": "https://example.com/copilot",
            "linked_repo_url": None,
            "title": "Copilot",
            "author_name": "Acme",
            "first_observed_at": "2026-03-01T00:00:00Z",
            "latest_observed_at": "2026-03-01T00:00:00Z",
            "normalization_version": "product_hunt_v1",
        }
        existing_products = [
            {"product_id": "prod_1", "canonical_homepage_url": "https://example.com/copilot", "normalized_name": "copilot"},
            {"product_id": "prod_2", "canonical_homepage_url": "https://example.com/copilot", "normalized_name": "copilot"},
        ]

        resolution = resolve_source_item(source_item, existing_products=existing_products)
        self.assertIsNone(resolution["product"])
        self.assertEqual(resolution["entity_match_candidate"]["suggested_action"], "review")


if __name__ == "__main__":
    unittest.main()
