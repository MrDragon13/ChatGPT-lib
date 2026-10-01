from __future__ import annotations

import shutil
from pathlib import Path


def copy_fixture_repo(tmp_path: Path) -> Path:
    src = Path(__file__).parents[1] / "fixtures" / "media_repo"
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)
    return dst
