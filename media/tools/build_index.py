from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import iter_yaml_files, load_yaml, write_jsonl
from .model import compact_signal, effective_metadata


def _collection_memberships(media_root: Path) -> dict[str, list[str]]:
    memberships: dict[str, list[str]] = {}
    for path in iter_yaml_files(media_root / 'data/collections'):
        doc = load_yaml(path) or {}
        collection_id = doc.get('id')
        if not collection_id:
            continue
        for member in doc.get('member_ids') or []:
            memberships.setdefault(member, []).append(collection_id)
    for values in memberships.values():
        values.sort()
    return memberships


def build_index_rows(media_root: Path) -> list[dict[str, Any]]:
    memberships = _collection_memberships(media_root)
    rows: list[dict[str, Any]] = []
    for path in iter_yaml_files(media_root / 'data/works'):
        work = load_yaml(path) or {}
        ident = work.get('identity') or {}
        meta = effective_metadata(work)
        semantic = ((work.get('metadata') or {}).get('semantic') or {})
        row: dict[str, Any] = {
            'id': work.get('id'),
            'format': ident.get('format'),
            'medium': ident.get('medium'),
            'title_original': ident.get('title_original'),
            'title_ru': ident.get('title_ru'),
            'alternate_titles': ident.get('alternate_titles') or [],
            'year': ident.get('year'),
            'runtime_min': meta.get('runtime_min'),
            'genres': sorted(meta.get('genres') or []),
            'traits': sorted({x.get('term') for x in semantic.get('traits') or [] if x.get('term')}),
            'viewer': {},
            'groups': {},
            'interest': {},
            'collections': memberships.get(work.get('id'), []),
        }
        for target, signal in sorted((work.get('viewer_signals') or {}).items()):
            compact = compact_signal(signal)
            if compact:
                row['viewer'][target] = compact
        for target, signal in sorted((work.get('group_signals') or {}).items()):
            compact = compact_signal(signal)
            if compact:
                row['groups'][target] = compact
        for target, state in sorted((work.get('target_states') or {}).items()):
            interest = (state or {}).get('interest')
            if interest:
                row['interest'][target] = interest
        rows.append(row)
    rows.sort(key=lambda r: r['id'])
    return rows


def write_index(media_root: Path, output: Path | None = None) -> Path:
    output = output or media_root / 'generated/index.jsonl'
    write_jsonl(output, build_index_rows(media_root))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Build compact media retrieval index')
    parser.add_argument('media_root', nargs='?', default='media')
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    out = write_index(Path(args.media_root), Path(args.output) if args.output else None)
    print(out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
