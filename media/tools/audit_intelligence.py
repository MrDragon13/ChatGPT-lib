from __future__ import annotations

import argparse
import json
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
    return sorted(
        (path for path in directory.glob(pattern) if path.is_file()),
        key=lambda path: path.as_posix(),
    )


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

    return tuple(
        sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())
    )


def _normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_input_digest(repo_root: Path) -> str:
    root = Path(repo_root)
    digest = sha256()
    for path in sorted(
        audit_input_paths(root), key=lambda item: item.relative_to(root).as_posix()
    ):
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
    return any(
        (signal.get("viewing") or {}).get("status") is not None for signal in signals
    )


def _is_watched_for_target(
    entity: dict[str, Any],
    target: str,
    viewers: set[str],
    groups: dict[str, list[str]],
) -> bool:
    viewer_signals = entity.get("viewer_signals") or {}
    if target in viewers:
        return (
            (viewer_signals.get(target) or {}).get("viewing") or {}
        ).get("status") == "watched"

    members = groups.get(target, [])
    return bool(members) and all(
        ((viewer_signals.get(member) or {}).get("viewing") or {}).get("status")
        == "watched"
        for member in members
    )


def _ratings(signals: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for signal in signals:
        rating = signal.get("rating") or {}
        if rating.get("score") is not None:
            result.append(rating)
    return result


def _has_structured_feedback(signals: Iterable[dict[str, Any]]) -> bool:
    return any(bool((signal.get("feedback") or {}).get("signals")) for signal in signals)


def _coverage(numerator: int, denominator: int) -> dict[str, int]:
    return {"numerator": numerator, "denominator": denominator}


def _signal_metrics(
    entities: list[dict[str, Any]],
    target: str,
    viewers: set[str],
    groups: dict[str, list[str]],
) -> dict[str, Any]:
    viewing_count = 0
    watched_count = 0
    rated_count = 0
    structured_feedback_count = 0
    rated_structured_feedback_count = 0
    rating_sources: Counter[str] = Counter()
    unclassified = 0
    rating_scores: list[float] = []

    for entity in entities:
        signals = _target_signals(entity, target, viewers, groups)
        if _has_viewing(signals):
            viewing_count += 1
        if _is_watched_for_target(entity, target, viewers, groups):
            watched_count += 1

        entity_ratings = _ratings(signals)
        has_rating = bool(entity_ratings)
        if has_rating:
            rated_count += 1
        for rating in entity_ratings:
            score = rating.get("score")
            if score is not None:
                rating_scores.append(float(score))
            source = rating.get("source")
            if isinstance(source, str) and source in KNOWN_RATING_SOURCES:
                rating_sources[source] += 1
            else:
                unclassified += 1

        has_structured_feedback = _has_structured_feedback(signals)
        if has_structured_feedback:
            structured_feedback_count += 1
            if has_rating:
                rated_structured_feedback_count += 1

    mean_score = (
        round(sum(rating_scores) / len(rating_scores), 3) if rating_scores else None
    )
    return {
        "viewing_count": viewing_count,
        "watched_count": watched_count,
        "rated_count": rated_count,
        "rating_sources": rating_sources,
        "unclassified_source": unclassified,
        "rating_scores": rating_scores,
        "mean_score": mean_score,
        "structured_feedback_count": structured_feedback_count,
        "rated_structured_feedback_count": rated_structured_feedback_count,
    }


def _combine_signal_metrics(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    scores = [*left["rating_scores"], *right["rating_scores"]]
    return {
        "viewing_count": left["viewing_count"] + right["viewing_count"],
        "watched_count": left["watched_count"] + right["watched_count"],
        "rated_count": left["rated_count"] + right["rated_count"],
        "rating_sources": left["rating_sources"] + right["rating_sources"],
        "unclassified_source": left["unclassified_source"]
        + right["unclassified_source"],
        "rating_scores": scores,
        "mean_score": round(sum(scores) / len(scores), 3) if scores else None,
        "structured_feedback_count": left["structured_feedback_count"]
        + right["structured_feedback_count"],
        "rated_structured_feedback_count": left["rated_structured_feedback_count"]
        + right["rated_structured_feedback_count"],
    }


def _viewing_metric(metrics: dict[str, Any], denominator: int) -> dict[str, Any]:
    result: dict[str, Any] = _coverage(metrics["viewing_count"], denominator)
    result["watched"] = _coverage(metrics["watched_count"], denominator)
    return result


def _rating_metric(metrics: dict[str, Any], denominator: int) -> dict[str, Any]:
    result: dict[str, Any] = _coverage(metrics["rated_count"], denominator)
    result["by_source"] = dict(sorted(metrics["rating_sources"].items()))
    result["unclassified_source"] = metrics["unclassified_source"]
    result["mean_score"] = metrics["mean_score"]
    return result


def _feedback_metric(metrics: dict[str, Any], denominator: int) -> dict[str, Any]:
    result: dict[str, Any] = _coverage(
        metrics["structured_feedback_count"], denominator
    )
    result["rated"] = _coverage(
        metrics["rated_structured_feedback_count"], metrics["rated_count"]
    )
    return result


def _semantic_trait_count(work: dict[str, Any]) -> int:
    semantic = ((work.get("metadata") or {}).get("semantic") or {})
    return sum(
        1
        for trait in semantic.get("traits") or []
        if isinstance(trait, dict) and trait.get("term")
    )


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
        work_metrics = _signal_metrics(works, target, viewers, groups)
        collection_metrics = _signal_metrics(collections, target, viewers, groups)
        entity_metrics = _combine_signal_metrics(work_metrics, collection_metrics)

        viewing[target] = {
            "works": _viewing_metric(work_metrics, len(works)),
            "collections": _viewing_metric(collection_metrics, len(collections)),
            "entities": _viewing_metric(
                entity_metrics, len(works) + len(collections)
            ),
        }
        ratings[target] = {
            "works": _rating_metric(work_metrics, len(works)),
            "collections": _rating_metric(collection_metrics, len(collections)),
            "entities": _rating_metric(
                entity_metrics, len(works) + len(collections)
            ),
        }
        feedback[target] = {
            "works": _feedback_metric(work_metrics, len(works)),
            "collections": _feedback_metric(collection_metrics, len(collections)),
            "entities": _feedback_metric(
                entity_metrics, len(works) + len(collections)
            ),
        }

    vocabulary = load_yaml(media_root / "vocabulary.yaml") or {}
    terms = vocabulary.get("terms") or {} if isinstance(vocabulary, dict) else {}
    works_with_fingerprint = sum(
        1 for work in works if _semantic_trait_count(work) > 0
    )

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


def _json_line(value: dict[str, Any]) -> str:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def _write_baseline(
    payload: dict[str, Any],
    output: Path,
    *,
    source_revision: str,
    generated_at: str,
) -> tuple[Path, Path]:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_json_line(payload), encoding="utf-8", newline="\n")
    meta_path = output.with_suffix(".meta.json")
    meta = {
        "baseline": output.name,
        "canonical_input_digest": payload["canonical_input_digest"],
        "generated_at": generated_at,
        "payload_schema_version": payload["schema_version"],
        "source_revision": source_revision,
    }
    meta_path.write_text(_json_line(meta), encoding="utf-8", newline="\n")
    return output, meta_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Media Intelligence coverage and evidence state"
    )
    parser.add_argument("repo_root", nargs="?", default=".")
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument("--write-baseline")
    parser.add_argument("--source-revision")
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    payload = collect_intelligence_audit(Path(args.repo_root))
    if args.write_baseline:
        if not args.source_revision or not args.generated_at:
            parser.error("--write-baseline requires --source-revision and --generated-at")
        output, _ = _write_baseline(
            payload,
            Path(args.write_baseline),
            source_revision=args.source_revision,
            generated_at=args.generated_at,
        )
        print(output)
    else:
        print(_json_line(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
