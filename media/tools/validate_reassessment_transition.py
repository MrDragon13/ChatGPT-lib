from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from media.service.reassessment_validation import validate_reassessment_transition


def _load_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one reassessment pilot base-to-head transition")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument(
        "--operation",
        required=True,
        choices=("reserve_reassessment_session", "complete_reassessment_item", "close_reassessment_session"),
    )
    parser.add_argument("--operation-receipt", required=True)
    args = parser.parse_args(argv)

    try:
        base = _load_object(Path(args.base), "base ledger")
        head = _load_object(Path(args.head), "head ledger")
        receipt = _load_object(Path(args.operation_receipt), "operation receipt")
    except ValueError as exc:
        print(json.dumps({"status": "error", "issues": [{"code": "input", "message": str(exc)}]}, sort_keys=True))
        return 2

    issues = validate_reassessment_transition(base, head, operation=args.operation, receipt=receipt)
    if issues:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "issues": [{"code": issue.code, "message": issue.message} for issue in issues],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps({"status": "ok", "issues": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
