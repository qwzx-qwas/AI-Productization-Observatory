"""Command-line entrypoints for the minimal runnable baseline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.common.config import AppConfig, require_environment_variables
from src.common.errors import BlockedReplayError, ConfigError, ContractValidationError, ObservatoryError
from src.common.files import load_yaml
from src.common.logging_utils import configure_logging, get_logger
from src.common.schema import validate_schema_document
from src.devtools.quality import format_python, lint_python, typecheck_python
from src.runtime.migrations import migration_plan
from src.runtime.replay import build_default_mart, replay_source_window


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apo-observatory", description="Minimal runnable baseline for the observatory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="Bootstrap local runtime directories and dependency checks.")
    subparsers.add_parser("validate-schemas", help="Validate JSON schema documents under schemas/.")
    subparsers.add_parser("validate-configs", help="Validate YAML config artifacts under configs/.")

    env_parser = subparsers.add_parser("validate-env", help="Fail when required environment variables are missing.")
    env_parser.add_argument("--require", nargs="+", required=True)

    lint_parser = subparsers.add_parser("lint", help="Run lightweight Python lint checks.")
    lint_parser.add_argument("paths", nargs="*", default=["src", "tests"])

    format_parser = subparsers.add_parser("format", help="Strip trailing whitespace and ensure trailing newlines.")
    format_parser.add_argument("paths", nargs="*", default=["src", "tests"])

    typecheck_parser = subparsers.add_parser("typecheck", help="Run annotation coverage checks on Python modules.")
    typecheck_parser.add_argument("paths", nargs="*", default=["src", "tests"])

    replay_parser = subparsers.add_parser("replay-window", help="Replay a deterministic per-source window fixture.")
    replay_parser.add_argument("--source", required=True)
    replay_parser.add_argument("--window", required=True)

    subparsers.add_parser("build-mart-window", help="Build the default mart fixture into a local mart artifact.")

    migrate_parser = subparsers.add_parser("migrate", help="Show the reserved migration entrypoint plan.")
    migrate_parser.add_argument("--plan", action="store_true")

    return parser


def validate_configs(config: AppConfig) -> int:
    source_registry = load_yaml(config.config_dir / "source_registry.yaml")
    sources = source_registry.get("sources", [])
    source_ids = [entry["source_id"] for entry in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ContractValidationError("source_registry.yaml contains duplicate source_id values")
    if not all(isinstance(entry.get("enabled"), bool) for entry in sources):
        raise ContractValidationError("Every source_registry entry must define a boolean enabled field")
    return len(sources)


def validate_schemas(config: AppConfig) -> int:
    schema_paths = sorted(config.schema_dir.glob("*.json"))
    for schema_path in schema_paths:
        validate_schema_document(schema_path)
    return len(schema_paths)


def _quality_paths(values: list[str]) -> list[Path]:
    return [Path(value).resolve() for value in values]


def bootstrap_install(config: AppConfig) -> str:
    config.raw_store_dir.mkdir(parents=True, exist_ok=True)
    config.task_store_path.parent.mkdir(parents=True, exist_ok=True)
    config.mart_output_dir.mkdir(parents=True, exist_ok=True)
    return "bootstrap_complete"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = AppConfig.from_env(Path.cwd())
        configure_logging(config.log_level)
        logger = get_logger("cli")

        if args.command == "install":
            status = bootstrap_install(config)
            logger.info(f"local install bootstrap status={status}")
            return 0

        if args.command == "validate-schemas":
            count = validate_schemas(config)
            logger.info(f"validated {count} schema documents")
            return 0

        if args.command == "validate-configs":
            count = validate_configs(config)
            logger.info(f"validated {count} source registry entries")
            return 0

        if args.command == "validate-env":
            require_environment_variables(args.require)
            logger.info(f"validated env vars: {', '.join(args.require)}")
            return 0

        if args.command == "lint":
            result = lint_python(_quality_paths(args.paths))
            logger.info(f"lint checked {result.checked_files} files")
            return 0

        if args.command == "format":
            result = format_python(_quality_paths(args.paths))
            logger.info(f"format checked {result.checked_files} files and changed {result.changed_files}")
            return 0

        if args.command == "typecheck":
            result = typecheck_python(_quality_paths(args.paths))
            logger.info(f"typecheck checked {result.checked_files} files")
            return 0

        if args.command == "replay-window":
            result = replay_source_window(source_code=args.source, window=args.window, config=config)
            replay_logger = get_logger(
                "cli",
                source_id=result["crawl_run"]["source_id"],
                run_id=result["crawl_run"]["crawl_run_id"],
                task_id=result["task_id"],
                resolution_status="succeeded",
            )
            replay_logger.info("replay finished")
            print(
                f"task_id={result['task_id']} raw_records={len(result['raw_records'])} "
                f"source_items={len(result['source_items'])}"
            )
            return 0

        if args.command == "build-mart-window":
            mart = build_default_mart(config)
            print(f"mart_rows={len(mart['top_jtbd_products_30d'])} attention_rows={len(mart['attention_distribution_30d'])}")
            return 0

        if args.command == "migrate":
            if not args.plan:
                raise ConfigError("Only --plan is implemented in the minimal baseline")
            print(migration_plan())
            return 0

        raise ConfigError(f"Unsupported command: {args.command}")
    except BlockedReplayError as exc:
        print(f"Replay blocked: {exc}", file=sys.stderr)
        return 3
    except (ConfigError, ContractValidationError, ObservatoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
