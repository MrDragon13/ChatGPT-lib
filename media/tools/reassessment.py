from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from media.repository.yaml_repo import YamlRepository
from media.service.reassessment import PILOT_ID, build_initial_ledger, ledger_bytes, read_ledger


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m media.tools.reassessment")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--repo-root", required=True)
    init.add_argument("--output", required=True)
    init.add_argument("--base-revision", required=True)
    init.add_argument("--baseline-path", required=True)
    init.add_argument("--force", action="store_true")

    summary = sub.add_parser("summary")
    summary.add_argument("ledger")
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _summary(document: dict[str, Any]) -> dict[str, Any]:
    frozen_items = (document.get("frozen_cohort") or {}).get("items") or {}
    lifecycle_items = document.get("items") or {}
    strata = Counter(
        item.get("stratum")
        for item in frozen_items.values()
        if isinstance(item, dict) and isinstance(item.get("stratum"), str)
    )
    statuses = Counter(
        item.get("status")
        for item in lifecycle_items.values()
        if isinstance(item, dict) and isinstance(item.get("status"), str)
    )
    return {
        "pilot_id": document.get("pilot_id"),
        "pilot_status": document.get("pilot_status"),
        "cohort_total": len((document.get("frozen_cohort") or {}).get("work_ids") or []),
        "strata": dict(sorted(strata.items())),
        "statuses": dict(sorted(statuses.items())),
        "sessions_total": len(document.get("sessions") or []),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "summary":
        print(json.dumps(_summary(read_ledger(Path(args.ledger))), ensure_ascii=False, sort_keys=True))
        return 0

    repo_root = Path(args.repo_root)
    output = Path(args.output)
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing ledger: {output}")

    baseline_path = Path(args.baseline_path)
    baseline_file = baseline_path if baseline_path.is_absolute() else repo_root / baseline_path
    baseline_document = _load_json(baseline_file)
    ledger = build_initial_ledger(
        YamlRepository(repo_root / "media"),
        pilot_id=PILOT_ID,
        base_revision=args.base_revision,
        baseline_path=args.baseline_path,
        baseline_document=baseline_document,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(ledger_bytes(ledger))
    print(json.dumps(_summary(ledger), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
