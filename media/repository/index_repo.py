from __future__ import annotations

from pathlib import Path
from typing import Any

from media.tools.common import iter_jsonl


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


class IndexRepository:
    def __init__(self, path: Path):
        self.path = Path(path)

    def rows(self) -> list[dict[str, Any]]:
        return [row for _, row in iter_jsonl(self.path)]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        needle = _norm(query)
        results = []
        for row in self.rows():
            values = [row.get("id"), row.get("title_original"), row.get("title_ru"), *(row.get("alternate_titles") or [])]
            haystacks = [_norm(str(value)) for value in values if value]
            if any(needle in value for value in haystacks):
                results.append(row)
        results.sort(key=lambda row: row["id"])
        return results[:limit]

    def get(self, work_id: str) -> dict[str, Any] | None:
        for row in self.rows():
            if row.get("id") == work_id:
                return row
        return None
