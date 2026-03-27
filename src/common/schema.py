"""Schema loading and validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from src.common.errors import ContractValidationError
from src.common.files import load_json


def load_schema(schema_path: Path) -> dict[str, Any]:
    return load_json(schema_path)


def validate_schema_document(schema_path: Path) -> None:
    schema = load_schema(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ContractValidationError(f"Invalid schema document at {schema_path}: {exc.message}") from exc


def validate_instance(instance: dict[str, Any], schema_path: Path) -> None:
    schema = load_schema(schema_path)
    try:
        Draft202012Validator(schema).validate(instance)
    except ValidationError as exc:
        raise ContractValidationError(f"Schema validation failed for {schema_path.name}: {exc.message}") from exc
