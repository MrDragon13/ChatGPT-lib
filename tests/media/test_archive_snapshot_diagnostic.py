from __future__ import annotations

import base64
from pathlib import Path

from media.tools.archive_library import render_library_archive


def test_emit_archive_review_snapshot():
    payload=render_library_archive(Path("media")).encode("utf-8")
    encoded=base64.b64encode(payload).decode("ascii")
    raise AssertionError(f"MEDIA_ARCHIVE_B64_BEGIN{encoded}MEDIA_ARCHIVE_B64_END")
