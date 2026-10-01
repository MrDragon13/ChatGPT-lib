from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def iter_yaml_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}],
        key=lambda p: p.name,
    )


def iter_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: JSONL row must be an object")
            yield line_no, value


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
