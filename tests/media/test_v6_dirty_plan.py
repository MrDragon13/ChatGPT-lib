from copy import deepcopy

from media.domain.changeset import MutationPlan
from media.repository.yaml_repo import YamlRepository
from media.service.derived import DirtyPlan, derive_dirty_plan
from media.tools.common import dump_yaml, load_yaml
from tests.media.fixture_repo import copy_fixture_repo


UUID = "123e4567-e89b-42d3-a456-426614174220"


def plan(*domains, changed_entities=(), documents=None):
    return MutationPlan(
        operation_id=UUID,
        operation="test",
        changed_entities=tuple(changed_entities),
        documents=documents or {},
        changed_domains=tuple(domains),
    )


def test_viewer_primary_rebuilds_index_primary_and_member_groups(tmp_path):
    root = copy_fixture_repo(tmp_path)
    dirty = derive_dirty_plan(
        YamlRepository(root / "media"),
        plan("viewer:primary", "viewer:primary"),
    )

    assert dirty == DirtyPlan(
        rebuild_index=True,
        rebuild_profile_targets=("couple", "primary"),
    )


def test_partner_viewer_does_not_rebuild_primary(tmp_path):
    root = copy_fixture_repo(tmp_path)
    dirty = derive_dirty_plan(YamlRepository(root / "media"), plan("viewer:partner"))

    assert dirty == DirtyPlan(
        rebuild_index=True,
        rebuild_profile_targets=("couple", "partner"),
    )


def test_metadata_and_interest_rebuild_only_index(tmp_path):
    root = copy_fixture_repo(tmp_path)
    repo = YamlRepository(root / "media")

    assert derive_dirty_plan(repo, plan("work.metadata")) == DirtyPlan(True, ())
    assert derive_dirty_plan(repo, plan("interest:primary")) == DirtyPlan(True, ())


def test_semantics_rebuilds_only_profiles_with_rating_evidence_for_work(tmp_path):
    root = copy_fixture_repo(tmp_path)
    work_path = root / "media/data/works/arrival-2016.yaml"
    document = load_yaml(work_path)
    document = deepcopy(document)
    document["viewer_signals"]["primary"]["rating"] = {
        "score": 9,
        "source": "explicit",
        "confidence": "exact",
    }
    dump_yaml(work_path, document)

    changed = deepcopy(document)
    changed["metadata"]["semantic"]["traits"] = [
        {"term": "pacing.slow", "source": "llm_inferred", "confidence": "medium"}
    ]
    dirty = derive_dirty_plan(
        YamlRepository(root / "media"),
        plan(
            "work.semantics",
            changed_entities=("arrival-2016",),
            documents={"media/data/works/arrival-2016.yaml": changed},
        ),
    )

    assert dirty == DirtyPlan(
        rebuild_index=True,
        rebuild_profile_targets=("couple", "primary"),
    )


def test_inferred_and_interaction_domains_rebuild_only_target_profile(tmp_path):
    root = copy_fixture_repo(tmp_path)
    repo = YamlRepository(root / "media")

    assert derive_dirty_plan(repo, plan("preferences.inferred:primary")) == DirtyPlan(
        False, ("primary",)
    )
    assert derive_dirty_plan(repo, plan("interaction:partner")) == DirtyPlan(
        False, ("partner",)
    )


def test_similarity_domain_has_no_generated_dependency(tmp_path):
    root = copy_fixture_repo(tmp_path)

    assert derive_dirty_plan(
        YamlRepository(root / "media"),
        plan("similarity:primary"),
    ) == DirtyPlan(False, ())
