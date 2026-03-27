"""Forward-only migration entry reserved for later database-backed runtime work."""

from __future__ import annotations


def migration_plan() -> dict[str, object]:
    return {
        "policy": "forward-only + additive-first",
        "status": "reserved_entrypoint",
        "next_steps": [
            "Add SQL migrations when the PostgreSQL task table is introduced.",
            "Keep replay/task contracts stable while storage evolves.",
        ],
    }
