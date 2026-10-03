from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from media.domain.changeset import MutationPlan
from media.domain.commands import SetSemanticFingerprintCommand
from media.domain.errors import CommandValidationError
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_work
from media.tools.common import load_yaml


def _date(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


def _vocabulary(repo: YamlRepository) -> dict[str, dict[str, Any]]:
    doc=load_yaml(repo.media_root / "vocabulary.yaml") or {}
    return dict(doc.get("terms") or {})


def plan_set_semantic_fingerprint(repo: YamlRepository, command: SetSemanticFingerprintCommand, *, now: datetime | None = None) -> MutationPlan:
    record=resolve_work(repo,command.work_ref); vocab=_vocabulary(repo)
    traits=[]
    for item in command.traits:
        term=item["term"]; meta=vocab.get(term)
        if meta is None: raise CommandValidationError(f"unknown vocabulary term: {term}")
        if meta.get("kind")=="reaction": raise CommandValidationError(f"reaction term cannot be a film trait: {term}")
        traits.append(copy.deepcopy(dict(item)))
    doc=copy.deepcopy(dict(record.data)); metadata=doc.setdefault("metadata",{}); semantic=metadata.setdefault("semantic",{})
    changed=semantic.get("traits")!=traits
    if changed:
        semantic["traits"]=traits; doc.setdefault("provenance",{})["updated_at"]=_date(now)
    path=str(record.path.relative_to(repo.media_root.parent)).replace("\\","/")
    return MutationPlan(command.operation_id,"set_semantic_fingerprint",(record.id,) if changed else (),{path:doc} if changed else {},changed,())
