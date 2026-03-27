"""Lightweight local quality commands that do not depend on extra tooling."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.common.errors import ContractValidationError


@dataclass
class QualityResult:
    checked_files: int
    changed_files: int = 0


def _iter_python_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(candidate for candidate in path.rglob("*.py") if "__pycache__" not in candidate.parts))
    return files


def lint_python(paths: Iterable[Path]) -> QualityResult:
    checked = 0
    for file_path in _iter_python_files(paths):
        checked += 1
        content = file_path.read_text(encoding="utf-8")
        if "\t" in content:
            raise ContractValidationError(f"Tab indentation is not allowed: {file_path}")
        for line_number, line in enumerate(content.splitlines(), start=1):
            if line.rstrip(" ") != line:
                raise ContractValidationError(f"Trailing spaces found in {file_path}:{line_number}")
        ast.parse(content, filename=str(file_path))
    return QualityResult(checked_files=checked)


def format_python(paths: Iterable[Path]) -> QualityResult:
    changed = 0
    files = _iter_python_files(paths)
    for file_path in files:
        original = file_path.read_text(encoding="utf-8")
        formatted = "\n".join(line.rstrip() for line in original.splitlines())
        if original.endswith("\n") or not original:
            formatted = formatted + "\n"
        if formatted != original:
            file_path.write_text(formatted, encoding="utf-8")
            changed += 1
    return QualityResult(checked_files=len(files), changed_files=changed)


def typecheck_python(paths: Iterable[Path]) -> QualityResult:
    checked = 0
    for file_path in _iter_python_files(paths):
        checked += 1
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                real_args = [argument for argument in node.args.args if argument.arg not in {"self", "cls"}]
                has_annotations = all(argument.annotation is not None for argument in real_args)
                if node.returns is None or not has_annotations:
                    raise ContractValidationError(f"Public function lacks full annotations: {file_path}:{node.lineno}")
    return QualityResult(checked_files=checked)
