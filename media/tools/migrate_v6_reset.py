from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from media.tools.archive_library import verify_library_archive
from media.tools.rebuild import rebuild_generated


class ResetSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResetPlan:
    archive_path: str
    remove_paths: tuple[str, ...]
    preserve_paths: tuple[str, ...]


def _relative(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _files(directory: Path, pattern: str) -> Iterable[Path]:
    if not directory.exists():
        return ()
    return tuple(sorted(path for path in directory.glob(pattern) if path.is_file()))


def _removal_candidates(repo_root: Path) -> tuple[Path, ...]:
    media=repo_root/"media"
    paths: list[Path]=[]
    specs=(
        (media/"data/works","*.yaml"),
        (media/"data/collections","*.yaml"),
        (media/"data/relations/similarity","*.yaml"),
        (media/"data/interactions","*.jsonl"),
        (media/"preferences/inferred","*.yaml"),
        (media/"baselines","intelligence-stage-a*.json"),
        (repo_root/".media/operations","*.json"),
    )
    for directory,pattern in specs:
        paths.extend(_files(directory,pattern))

    pilot=media/"pilots/legacy-reassessment-primary.json"
    if pilot.is_file():
        paths.append(pilot)

    return tuple(sorted(set(paths),key=lambda path:_relative(repo_root,path)))


def _preserved_paths(repo_root: Path) -> tuple[str, ...]:
    media=repo_root/"media"
    paths: list[Path]=[]
    paths.extend(_files(media/"preferences/explicit","*.yaml"))
    vocabulary=media/"vocabulary.yaml"
    if vocabulary.is_file():
        paths.append(vocabulary)
    for config in _files(media/"config","*.yaml"):
        paths.append(config)
    return tuple(sorted({_relative(repo_root,path) for path in paths}))


def _assert_no_pending_requests(repo_root: Path) -> None:
    pending=tuple(_files(repo_root/".media/requests","*.json"))
    if pending:
        joined=", ".join(_relative(repo_root,path) for path in pending)
        raise ResetSafetyError(f"pending media request(s) must be resolved before reset: {joined}")


def _verify_archive_or_raise(repo_root: Path, archive: Path) -> None:
    errors=verify_library_archive(repo_root,archive)
    if errors:
        raise ResetSafetyError("archive verification failed: "+"; ".join(errors))


def plan_v6_reset(repo_root: Path, archive: Path) -> ResetPlan:
    repo_root=Path(repo_root).resolve()
    archive=Path(archive)
    if not archive.is_absolute():
        archive=repo_root/archive
    _verify_archive_or_raise(repo_root,archive)
    _assert_no_pending_requests(repo_root)
    return ResetPlan(
        archive_path=_relative(repo_root,archive),
        remove_paths=tuple(_relative(repo_root,path) for path in _removal_candidates(repo_root)),
        preserve_paths=_preserved_paths(repo_root),
    )


def _clear_generated(media_root: Path) -> None:
    index=media_root/"generated/index.jsonl"
    if index.exists():
        index.unlink()
    profiles=media_root/"generated/profiles"
    if profiles.exists():
        for path in sorted(profiles.glob("*.yaml")):
            if path.is_file():
                path.unlink()
    database=media_root/"generated/database.sqlite"
    if database.exists():
        database.unlink()


def apply_v6_reset(repo_root: Path, archive: Path) -> ResetPlan:
    repo_root=Path(repo_root).resolve()
    plan=plan_v6_reset(repo_root,archive)

    for rel in plan.remove_paths:
        path=repo_root/rel
        if path.exists():
            path.unlink()

    media=repo_root/"media"
    for directory in (
        media/"data/works",
        media/"data/collections",
        media/"data/relations/similarity",
        media/"data/interactions",
        media/"preferences/inferred",
        media/"pilots",
        media/"baselines",
        repo_root/".media/operations",
        repo_root/".media/requests",
        media/"generated/profiles",
    ):
        directory.mkdir(parents=True,exist_ok=True)

    _clear_generated(media)
    rebuild_generated(media)
    return plan


def _parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description="Plan or apply the guarded one-time Media Intelligence v6 reset.")
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--format",choices=("json","text"),default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args=_parser().parse_args(argv)
    try:
        plan=apply_v6_reset(args.repo_root,args.archive) if args.apply else plan_v6_reset(args.repo_root,args.archive)
    except ResetSafetyError as exc:
        if args.format=="json":
            print(json.dumps({"status":"blocked","error":str(exc)},ensure_ascii=False,sort_keys=True))
        else:
            print(f"BLOCKED: {exc}")
        return 2

    payload={
        "status":"applied" if args.apply else "planned",
        **asdict(plan),
    }
    if args.format=="json":
        print(json.dumps(payload,ensure_ascii=False,sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        print(f"archive: {plan.archive_path}")
        print(f"remove: {len(plan.remove_paths)}")
        for path in plan.remove_paths:
            print(f"  - {path}")
        print(f"preserve: {len(plan.preserve_paths)}")
        for path in plan.preserve_paths:
            print(f"  + {path}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
