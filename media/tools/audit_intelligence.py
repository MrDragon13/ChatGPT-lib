from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from media.repository.yaml_repo import YamlRepository
from media.service.recommendation_pool import filter_eligible_candidate_rows
from media.tools.build_index import build_index_rows
from media.tools.build_profiles import build_profile
from media.tools.common import iter_jsonl, iter_yaml_files, load_yaml
from media.tools.validate import validate_repository


KNOWN_RATING_SOURCES = {"explicit", "explicit_approx", "inferred", "none"}


def _existing_files(directory: Path, pattern: str) -> list[Path]:
    if not directory.exists():
        return []
    return sorted((path for path in directory.glob(pattern) if path.is_file()), key=lambda path: path.as_posix())


def audit_input_paths(repo_root: Path) -> tuple[Path, ...]:
    root = Path(repo_root)
    media = root / "media"
    paths: list[Path] = []

    for path in (
        media / "config/viewers.yaml",
        media / "config/groups.yaml",
        media / "vocabulary.yaml",
    ):
        if path.is_file():
            paths.append(path)

    for relative, pattern in (
        ("data/works", "*.yaml"),
        ("data/collections", "*.yaml"),
        ("data/lists", "*.yaml"),
        ("data/tombstones", "*.yaml"),
        ("data/relations/similarity", "*.yaml"),
        ("data/interactions", "*.jsonl"),
        ("preferences/explicit", "*.yaml"),
        ("preferences/inferred", "*.yaml"),
    ):
        paths.extend(_existing_files(media / relative, pattern))

    return tuple(sorted(set(paths), key=lambda path: path.relative_to(root).as_posix()))


def _normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_input_digest(repo_root: Path) -> str:
    root = Path(repo_root)
    digest = sha256()
    for path in sorted(audit_input_paths(root), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = _normalized_bytes(path)
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return f"sha256:{digest.hexdigest()}"


def _documents(media_root: Path, relative: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in iter_yaml_files(media_root / relative):
        doc = load_yaml(path)
        if isinstance(doc, dict):
            result.append(doc)
    return result


def _target_signals(
    entity: dict[str, Any],
    target: str,
    viewers: set[str],
    groups: dict[str, list[str]],
) -> list[dict[str, Any]]:
    viewer_signals = entity.get("viewer_signals") or {}
    group_signals = entity.get("group_signals") or {}
    if target in viewers:
        signal = viewer_signals.get(target)
        return [signal] if isinstance(signal, dict) else []

    signals = [
        viewer_signals[member]
        for member in groups.get(target, [])
        if isinstance(viewer_signals.get(member), dict)
    ]
    direct = group_signals.get(target)
    if isinstance(direct, dict):
        signals.append(direct)
    return signals


def _has_viewing(signals: Iterable[dict[str, Any]]) -> bool:
    return any((signal.get("viewing") or {}).get("status") is not None for signal in signals)


def _ratings(signals: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for signal in signals:
        rating = signal.get("rating") or {}
        if rating.get("score") is not None:
            result.append(rating)
    return result


def _has_feedback(signals: Iterable[dict[str, Any]]) -> bool:
    for signal in signals:
        feedback = signal.get("feedback") or {}
        if feedback.get("summary") not in {None, ""} or feedback.get("signals"):
            return True
    return False


def _coverage(numerator: int, denominator: int) -> dict[str, int]:
    return {"numerator": numerator, "denominator": denominator}


def _signal_metrics(
    entities: list[dict[str, Any]],
    target: str,
    viewers: set[str],
    groups: dict[str, list[str]],
) -> tuple[int, int, Counter[str], int]:
    viewing_count = 0
    rated_count = 0
    feedback_count = 0
    rating_sources: Counter[str] = Counter()
    unclassified = 0

    for entity in entities:
        signals = _target_signals(entity, target, viewers, groups)
        if _has_viewing(signals):
            viewing_count += 1
        entity_ratings = _ratings(signals)
        if entity_ratings:
            rated_count += 1
        for rating in entity_ratings:
            source = rating.get("source")
            if isinstance(source, str) and source in KNOWN_RATING_SOURCES:
                rating_sources[source] += 1
            else:
                unclassified += 1
        if _has_feedback(signals):
            feedback_count += 1

    return viewing_count, rated_count, rating_sources, feedback_count, unclassified


def _semantic_trait_count(work: dict[str, Any]) -> int:
    semantic = ((work.get("metadata") or {}).get("semantic") or {})
    return sum(1 for trait in semantic.get("traits") or [] if isinstance(trait, dict) and trait.get("term"))


def _similarity_metrics(media_root: Path) -> dict[str, Any]:
    total = 0
    by_target: Counter[str] = Counter()
    for path in iter_yaml_files(media_root / "data/relations/similarity"):
        doc = load_yaml(path) or {}
        relations = list(doc.get("relations") or []) if isinstance(doc, dict) else []
        total += len(relations)
        target = doc.get("target") if isinstance(doc, dict) else None
        if isinstance(target, str):
            by_target[target] += len(relations)
    return {"relations_total": total, "by_target": dict(sorted(by_target.items()))}


def _interaction_metrics(media_root: Path) -> dict[str, Any]:
    total = 0
    by_type: Counter[str] = Counter()
    by_target: Counter[str] = Counter()
    directory = media_root / "data/interactions"
    if directory.exists():
        for path in sorted(directory.glob("*.jsonl")):
            if not path.is_file():
                continue
            for _, event in iter_jsonl(path):
                total += 1
                event_type = event.get("type")
                target = event.get("target")
                if isinstance(event_type, str):
                    by_type[event_type] += 1
                if isinstance(target, str):
                    by_target[target] += 1
    return {
        "events_total": total,
        "by_type": dict(sorted(by_type.items())),
        "by_target": dict(sorted(by_target.items())),
    }


def _profile_metrics(media_root: Path, targets: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for target in targets:
        profile = build_profile(media_root, target)
        affinities = profile.get("affinities") or {}
        confidence = Counter()
        for affinity in affinities.values():
            value = (affinity or {}).get("confidence")
            confidence[value if isinstance(value, str) else "unclassified"] += 1
        result[target] = {
            "affinities_total": len(affinities),
            "confidence": dict(sorted(confidence.items())),
        }
    return result


def _pool_metrics(
    media_root: Path,
    targets: list[str],
    viewers: set[str],
    groups: dict[str, list[str]],
) -> dict[str, Any]:
    rows = build_index_rows(media_root)
    result: dict[str, Any] = {}
    for target in targets:
        candidates = filter_eligible_candidate_rows(
            rows,
            target=target,
            viewers=viewers,
            groups=groups,
            only_unwatched=True,
            include_not_interested=False,
            runtime_max=None,
        )
        with_fingerprint = sum(1 for row in candidates if row.get("traits"))
        result[target] = {
            "pool_total": len(candidates),
            "with_fingerprint": with_fingerprint,
            "fingerprint_coverage": _coverage(with_fingerprint, len(candidates)),
        }
    return result


def collect_intelligence_audit(repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root)
    issues = validate_repository(root)
    if issues:
        preview = "; ".join(
            f"{issue.path} [{issue.code}] {issue.message}" for issue in issues[:5]
        )
        raise ValueError(f"invalid canonical media state: {preview}")

    media_root = root / "media"
    works = _documents(media_root, "data/works")
    collections = _documents(media_root, "data/collections")
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    targets = sorted(viewers | set(groups))

    viewing: dict[str, Any] = {}
    ratings: dict[str, Any] = {}
    feedback: dict[str, Any] = {}
    for target in targets:
        work_viewing, work_rated, work_sources, work_feedback, work_unclassified = _signal_metrics(
            works, target, viewers, groups
        )
        collection_viewing, collection_rated, collection_sources, collection_feedback, collection_unclassified = _signal_metrics(
            collections, target, viewers, groups
        )
        combined_sources = work_sources + collection_sources
        viewing[target] = {
            "works": _coverage(work_viewing, len(works)),
            "collections": _coverage(collection_viewing, len(collections)),
            "entities": _coverage(work_viewing + collection_viewing, len(works) + len(collections)),
        }
        ratings[target] = {
            "works": _coverage(work_rated, len(works)),
            "collections": _coverage(collection_rated, len(collections)),
            "entities": _coverage(work_rated + collection_rated, len(works) + len(collections)),
            "by_source": dict(sorted(combined_sources.items())),
            "unclassified_source": work_unclassified + collection_unclassified,
        }
        feedback[target] = {
            "works": _coverage(work_feedback, len(works)),
            "collections": _coverage(collection_feedback, len(collections)),
            "entities": _coverage(work_feedback + collection_feedback, len(works) + len(collections)),
        }

    vocabulary = load_yaml(media_root / "vocabulary.yaml") or {}
    terms = vocabulary.get("terms") or {} if isinstance(vocabulary, dict) else {}
    works_with_fingerprint = sum(1 for work in works if _semantic_trait_count(work) > 0)

    return {
        "schema_version": 1,
        "canonical_input_digest": canonical_input_digest(root),
        "inventory": {
            "works_total": len(works),
            "collections_total": len(collections),
            "entities_total": len(works) + len(collections),
        },
        "vocabulary": {"terms_total": len(terms)},
        "semantic_coverage": {
            "works": _coverage(works_with_fingerprint, len(works)),
        },
        "viewing": viewing,
        "ratings": ratings,
        "feedback": feedback,
        "profiles": _profile_metrics(media_root, targets),
        "similarity": _similarity_metrics(media_root),
        "interactions": _interaction_metrics(media_root),
        "recommendation_pool": _pool_metrics(media_root, targets, viewers, groups),
    }
