from __future__ import annotations

from pathlib import Path
from typing import Iterator

from media.tools.common import iter_yaml_files, load_yaml
from .canonical import WorkRecord


class YamlRepository:
    def __init__(self, media_root: Path):
        self.media_root = Path(media_root)

    def get_work(self, work_id: str) -> WorkRecord | None:
        direct = self.media_root / "data" / "works" / f"{work_id}.yaml"
        if direct.exists():
            data = load_yaml(direct)
            if isinstance(data, dict) and data.get("id") == work_id:
                return WorkRecord(direct, data)
        for record in self.iter_works():
            if record.id == work_id:
                return record
        return None

    def iter_works(self) -> Iterator[WorkRecord]:
        for path in iter_yaml_files(self.media_root / "data" / "works"):
            data = load_yaml(path)
            if isinstance(data, dict) and isinstance(data.get("id"), str):
                yield WorkRecord(path, data)

    def configured_targets(self) -> tuple[set[str], dict[str, list[str]]]:
        viewers_doc = load_yaml(self.media_root / "config" / "viewers.yaml") or {}
        groups_doc = load_yaml(self.media_root / "config" / "groups.yaml") or {}
        viewers = set((viewers_doc.get("viewers") or {}).keys())
        groups_raw = groups_doc.get("groups") or {}
        groups = {group_id: list((meta or {}).get("members") or []) for group_id, meta in groups_raw.items()}
        return viewers, groups
