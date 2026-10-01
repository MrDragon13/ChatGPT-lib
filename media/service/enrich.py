from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from media.domain.changeset import MutationPlan
from media.domain.commands import AddWorkCommand
from media.domain.errors import AmbiguousIdentityError, NotFoundError, ProviderUnavailableError
from media.domain.types import WorkRef
from media.providers.base import CanonicalMetadata, MetadataProvider, ProviderCandidate
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import normalize_title, resolve_work


def _all_profile_targets(repo: YamlRepository) -> tuple[str, ...]:
    viewers,groups=repo.configured_targets(); return tuple(sorted(viewers|set(groups)))

def select_provider_candidate(ref:WorkRef,candidates:list[ProviderCandidate])->ProviderCandidate:
    if ref.title is None: raise NotFoundError("provider search requires a title")
    needle=normalize_title(ref.title); plausible=[candidate for candidate in candidates if needle in {normalize_title(candidate.title),normalize_title(candidate.original_title)} and (ref.year is None or candidate.year==ref.year)]
    if not plausible: raise NotFoundError(f"provider work not found: {ref.title}")
    if len(plausible)>1: raise AmbiguousIdentityError(tuple(plausible))
    return plausible[0]

def make_work_id(repo:YamlRepository,metadata:CanonicalMetadata,candidate:ProviderCandidate)->str:
    title=str(metadata.identity.get("title_original") or metadata.identity.get("title_ru") or ""); ascii_title=unicodedata.normalize("NFKD",title).encode("ascii","ignore").decode("ascii"); slug=re.sub(r"[^a-z0-9]+","-",ascii_title.casefold()).strip("-"); year=metadata.identity.get("year"); base=f"{slug}-{year}" if slug and year else slug; fallback=f"tmdb-{candidate.media_type}-{candidate.provider_id}"
    if not base: base=fallback
    if repo.get_work(base) is not None: base=f"{base}-{fallback}"
    return base

def _existing_from_metadata(repo:YamlRepository,metadata:CanonicalMetadata):
    external=metadata.identity.get("external_ids") or {}; tmdb=external.get("tmdb") or {}
    if tmdb.get("media_type") and tmdb.get("id"):
        try: return resolve_work(repo,WorkRef(tmdb_media_type=tmdb["media_type"],tmdb_id=tmdb["id"]))
        except NotFoundError: pass
    if external.get("imdb"):
        try: return resolve_work(repo,WorkRef(imdb_id=external["imdb"]))
        except NotFoundError: pass
    return None

def plan_add_work(repo:YamlRepository,command:AddWorkCommand,provider:MetadataProvider|None,*,now:datetime|None=None)->MutationPlan:
    try: resolve_work(repo,command.work_ref); return MutationPlan(command.operation_id,"add_work",(),{},False,())
    except NotFoundError: pass
    if provider is None: raise ProviderUnavailableError("metadata provider is required to add an unknown work")
    if command.work_ref.tmdb_media_type and command.work_ref.tmdb_id: candidate=ProviderCandidate(command.work_ref.tmdb_media_type,command.work_ref.tmdb_id,command.work_ref.title or "",command.work_ref.title or "",command.work_ref.year)
    else: candidate=select_provider_candidate(command.work_ref,provider.search_work(command.work_ref.title or "",command.work_ref.year))
    metadata=provider.fetch_work(candidate.media_type,candidate.provider_id); existing=_existing_from_metadata(repo,metadata)
    if existing is not None: return MutationPlan(command.operation_id,"add_work",(),{},False,())
    work_id=make_work_id(repo,metadata,candidate); value=now or datetime.now(timezone.utc); day=value.date().isoformat(); document={"schema_version":4,"id":work_id,"entity_type":"work","identity":dict(metadata.identity),"metadata":{"external":dict(metadata.external)} if metadata.external else {},"provenance":{"created_at":day,"updated_at":day}}; path=f"media/data/works/{work_id}.yaml"; return MutationPlan(command.operation_id,"add_work",(work_id,),{path:document},True,_all_profile_targets(repo))
