from pathlib import Path

from media.tools.archive_library import verify_library_archive
from media.tools.migrate_v6_reset import plan_v6_reset


def test_exact_pre_reset_archive_and_dry_run_plan():
    root=Path(".").resolve()
    archive=root/"docs/archive/media-library-before-v6-reset-2026-10-07.md"

    assert verify_library_archive(root,archive)==[]
    plan=plan_v6_reset(root,archive)

    assert len([p for p in plan.remove_paths if p.startswith("media/data/works/")])==103
    assert len([p for p in plan.remove_paths if p.startswith("media/data/collections/")])==4
    assert len([p for p in plan.remove_paths if p.startswith("media/data/relations/similarity/")])==1
    assert len([p for p in plan.remove_paths if p.startswith("media/preferences/inferred/")])==3
    assert len([p for p in plan.remove_paths if p.startswith("media/baselines/intelligence-stage-a")])==2
    assert len([p for p in plan.remove_paths if p.startswith(".media/operations/")])==33
    assert "media/pilots/legacy-reassessment-primary.json" in plan.remove_paths
    assert len(plan.remove_paths)==147
    assert "media/preferences/explicit/primary.yaml" in plan.preserve_paths
    assert "media/vocabulary.yaml" in plan.preserve_paths
