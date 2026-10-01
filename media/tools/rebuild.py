from __future__ import annotations

import tempfile
from pathlib import Path

from .build_index import write_index
from .build_profiles import write_profiles


def rebuild_generated(media_root: Path, output_dir: Path | None = None) -> list[Path]:
    media_root=Path(media_root); out=media_root/'generated' if output_dir is None else Path(output_dir); out.mkdir(parents=True,exist_ok=True); paths=[write_index(media_root,out/'index.jsonl')]; paths.extend(write_profiles(media_root,out/'profiles')); return paths


def check_generated(media_root: Path) -> list[str]:
    media_root=Path(media_root); stale=[]
    with tempfile.TemporaryDirectory(prefix='media-rebuild-') as tmpdir:
        expected_root=Path(tmpdir)/'generated'; rebuild_generated(media_root,expected_root); expected_files=[path for path in expected_root.rglob('*') if path.is_file()]; actual_root=media_root/'generated'
        for expected in sorted(expected_files):
            rel=expected.relative_to(expected_root); actual=actual_root/rel
            if not actual.exists() or actual.read_bytes()!=expected.read_bytes(): stale.append(str(Path('generated')/rel).replace('\\','/'))
        expected_rel={path.relative_to(expected_root) for path in expected_files}
        if actual_root.exists():
            for actual in sorted(actual_root.rglob('*')):
                if not actual.is_file() or actual.name=='database.sqlite': continue
                rel=actual.relative_to(actual_root)
                if rel not in expected_rel: stale.append(str(Path('generated')/rel).replace('\\','/'))
    return sorted(set(stale))
