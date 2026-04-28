from __future__ import annotations

import unittest

from src.common.errors import ConfigError
from src.runtime.shadow_validation import (
    load_runtime_task_ddl,
    redact_shadow_database_url,
    validate_shadow_database_url,
)


class RuntimeShadowValidationUnitTests(unittest.TestCase):
    def test_shadow_database_url_redacts_password(self) -> None:
        redacted = redact_shadow_database_url(
            "postgresql://apo_shadow_user:secret-password@localhost:55432/apo_shadow"
        )

        self.assertEqual(
            redacted,
            "postgresql://apo_shadow_user:[REDACTED]@localhost:55432/apo_shadow",
        )
        self.assertNotIn("secret-password", redacted)

    def test_shadow_database_url_must_be_local_and_shadow_named(self) -> None:
        validate_shadow_database_url(
            "postgresql://apo_shadow_user:local-only@localhost:55432/apo_shadow"
        )

        with self.assertRaises(ConfigError):
            validate_shadow_database_url(
                "postgresql://apo_shadow_user:local-only@db.example.com:5432/apo_shadow"
            )
        with self.assertRaises(ConfigError):
            validate_shadow_database_url(
                "postgresql://app_user:local-only@localhost:55432/production"
            )

    def test_runtime_task_ddl_excludes_abstract_contract_templates(self) -> None:
        ddl = load_runtime_task_ddl()

        self.assertIn("CREATE TABLE IF NOT EXISTS runtime_task", ddl)
        self.assertIn("payload_json JSONB NOT NULL", ddl)
        self.assertNotIn("-- contract: runtime_task_claim_by_id_cas", ddl)
        self.assertNotIn(":worker_id", ddl)


if __name__ == "__main__":
    unittest.main()
