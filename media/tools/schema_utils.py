from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema.validators import validator_for
from referencing import Registry, Resource


def build_registry(schema_dir: Path) -> Registry:
    registry = Registry()
    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        uri = schema.get("$id")
        if not uri:
            raise ValueError(f"Schema {path} has no $id")
        registry = registry.with_resource(uri, Resource.from_contents(schema))
    return registry


def _format_path(parts: list[object]) -> str:
    if not parts:
        return "$"
    out = "$"
    for part in parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}"
    return out


def validate_against_schema(instance: Any, schema_name: str, schema_dir: Path) -> list[str]:
    path = schema_dir / schema_name
    schema = json.loads(path.read_text(encoding="utf-8"))
    cls = validator_for(schema)
    cls.check_schema(schema)
    validator = cls(schema, registry=build_registry(schema_dir))
    errors = [f"{_format_path(list(error.absolute_path))}: {error.message}" for error in validator.iter_errors(instance)]
    return sorted(errors)
