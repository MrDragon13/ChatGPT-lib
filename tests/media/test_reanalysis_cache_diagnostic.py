from dataclasses import asdict
from pathlib import Path

from media.service.reanalysis_status import get_reanalysis_status

ROOT = Path(__file__).parents[2]


def test_diagnostic_current_reanalysis_cache_values():
    values = {
        target: asdict(get_reanalysis_status(ROOT / "media", target))
        for target in ("primary", "partner")
    }
    raise AssertionError(repr(values))
