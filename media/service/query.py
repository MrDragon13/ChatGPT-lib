from __future__ import annotations

from pathlib import Path
from typing import Any

from media.domain.types import WorkRef
from media.repository.index_repo import IndexRepository
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_work


def search_works(media_root: Path, query: str, limit: int = 20) -> list[dict[str, Any]]:
    return IndexRepository(Path(media_root) / "generated" / "index.jsonl").search(query, limit=limit)


def show_work(media_root: Path, ref: str | WorkRef) -> dict[str, Any]:
    repo = YamlRepository(Path(media_root))
    if isinstance(ref, str):
        work_ref = WorkRef(id=ref) if repo.get_work(ref) is not None else WorkRef(title=ref)
    else:
        work_ref = ref
    return dict(resolve_work(repo, work_ref).data)
