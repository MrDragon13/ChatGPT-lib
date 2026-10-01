from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteRepository:
    def __init__(self, path: Path):
        self.path = Path(path)

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        needle = query.casefold()
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("SELECT id,title_original,title_ru,alternate_titles_json,year,runtime_min FROM works ORDER BY id").fetchall()
        finally:
            con.close()
        results = []
        for row in rows:
            alternate = json.loads(row["alternate_titles_json"] or "[]") if "alternate_titles_json" in row.keys() else []
            values = [row["id"], row["title_original"], row["title_ru"], *alternate]
            if any(needle in str(value or "").casefold() for value in values):
                results.append({key: row[key] for key in row.keys() if key != "alternate_titles_json"} | {"alternate_titles": alternate})
        return results[:limit]

    def get_work_summary(self, work_id: str) -> dict[str, Any] | None:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            row = con.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
        finally:
            con.close()
        return dict(row) if row is not None else None
