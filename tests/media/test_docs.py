from pathlib import Path

import json

from media.tools.common import load_yaml


def test_operational_docs_and_core_paths_exist():
    required=[
        'media/AGENTS.md','media/README.md','media/.gitignore','media/vocabulary.yaml',
        'media/config/viewers.yaml','media/config/groups.yaml','media/tools/validate.py',
        'media/tools/build_index.py','media/tools/build_profiles.py','media/tools/build_db.py',
        'docs/README.md','docs/architecture/overview.md','docs/architecture/media-model.md',
        'docs/architecture/intelligence.md','docs/architecture/write-pipeline.md',
        'docs/architecture/web-and-broker.md','docs/guides/operations.md',
        'docs/reference/media-commands.md','docs/reference/invariants.md','docs/status/current.md',
    ]
    for path in required:
        assert Path(path).exists(), path


def test_config_contains_only_initial_anonymous_targets():
    viewers=load_yaml(Path('media/config/viewers.yaml'))['viewers']
    groups=load_yaml(Path('media/config/groups.yaml'))['groups']
    assert set(viewers)=={'primary','partner'}
    assert groups=={'couple':{'members':['primary','partner']}}


def test_gitignore_excludes_sqlite_embeddings_and_image_cache():
    text=Path('media/.gitignore').read_text(encoding='utf-8')
    assert 'generated/database.sqlite' in text
    assert 'generated/embeddings/' in text
    assert 'generated/image-cache/' in text


def test_all_json_schemas_parse_and_have_ids():
    for path in Path('media/schemas').glob('*.schema.json'):
        doc=json.loads(path.read_text(encoding='utf-8'))
        assert doc['$schema'].endswith('2020-12/schema')
        assert doc['$id']


def test_operations_guide_matches_real_modules_and_agents_contract_keeps_guardrails():
    operations=Path('docs/guides/operations.md').read_text(encoding='utf-8')
    for cmd in ['python -m media.tools.validate .','python -m media.tools.build_index media','python -m media.tools.build_profiles media','python -m media.tools.build_db media']:
        assert cmd in operations
    agents=Path('media/AGENTS.md').read_text(encoding='utf-8')
    assert "## Жёсткие правила" in agents
    lowered = agents.lower()
    for fragment in ("схем", "неизвест", "временн", "полный набор проверок", "workflow", "словар"):
        assert fragment in lowered


def test_living_docs_define_refresh_metadata_as_manual_bulk_maintenance():
    operations=Path('docs/guides/operations.md').read_text(encoding='utf-8')
    reference=Path('docs/reference/media-commands.md').read_text(encoding='utf-8')
    agents=Path('media/AGENTS.md').read_text(encoding='utf-8')
    for text in (operations,reference,agents):
        assert 'refresh_metadata' in text
    assert 'all_movies' in operations
    assert 'manual' in operations.lower() or 'вручную' in operations.lower()
    assert 'all_movies' in agents
    assert 'manual-review' in agents


def test_living_docs_expose_v6_write_and_read_routes():
    commands=Path('docs/reference/media-commands.md').read_text(encoding='utf-8')
    intelligence=Path('docs/architecture/intelligence.md').read_text(encoding='utf-8')
    pipeline=Path('docs/architecture/write-pipeline.md').read_text(encoding='utf-8')
    for operation in (
        'record_media_entry',
        'set_inferred_preferences',
        'set_semantic_fingerprint',
        'record_recommendation_interaction',
        'set_work_similarity',
        'remove_work_similarity',
        'taste_context',
        'media_entry_context',
        'assess_candidate',
    ):
        assert operation in commands
    assert 'external discovery' in intelligence.lower() or 'внешн' in intelligence.lower()
    assert 'exact checked head' in pipeline.lower()
    assert 'v6_single_runner' in pipeline


def test_living_docs_expose_similarity_assessment_and_current_read_model():
    model=Path('docs/architecture/media-model.md').read_text(encoding='utf-8')
    intelligence=Path('docs/architecture/intelligence.md').read_text(encoding='utf-8')
    web=Path('docs/architecture/web-and-broker.md').read_text(encoding='utf-8')
    status=Path('docs/status/current.md').read_text(encoding='utf-8')
    assert 'media/data/relations/similarity/' in model
    assert 'similarity' in intelligence.lower()
    assert 'не является preference' in intelligence or 'не становится preference' in intelligence
    assert 'external' in model.lower()
    assert 'Current manifest version: v4' in web
    assert 'Media Intelligence v6' in status
    assert 'assess_candidate' in status
    assert 'manifest' in status.lower() and 'v4' in status


def test_v6_living_docs_define_observability_and_single_runner_merge_boundary():
    intelligence=Path('docs/architecture/intelligence.md').read_text(encoding='utf-8')
    pipeline=Path('docs/architecture/write-pipeline.md').read_text(encoding='utf-8')
    invariants=Path('docs/reference/invariants.md').read_text(encoding='utf-8')
    layout=Path('docs/reference/repository-layout.md').read_text(encoding='utf-8')
    status=Path('docs/status/current.md').read_text(encoding='utf-8')

    assert 'limitations' in intelligence
    assert 'assessment_coverage' in intelligence
    assert 'числен' in intelligence.lower() or 'numeric' in intelligence.lower()

    assert 'media/config/operation_path_policy.json' in pipeline
    assert 'v6_single_runner' in pipeline
    assert 'request-only' in pipeline
    assert 'GitHub API' in pipeline
    assert 'main' in pipeline

    assert 'path policy' in invariants.lower()
    assert 'media/config/operation_path_policy.json' in layout
    assert 'Media Intelligence v6' in status
    assert 'exact revision' in status


def test_write_pipeline_documents_final_v6_queue_and_removes_legacy_handoff():
    pipeline=Path('docs/architecture/write-pipeline.md').read_text(encoding='utf-8')
    assert 'media-data-pipeline' in pipeline
    assert 'cancel-in-progress: false' in pipeline
    assert 'queue: max' in pipeline
    assert 'единый `Media Command` runner' in pipeline
    assert 'security review' in pipeline


def test_living_docs_have_no_removed_split_workflow_names():
    paths = [
        Path(".media/README.md"),
        Path("docs/architecture/write-pipeline.md"),
        Path("docs/architecture/web-and-broker.md"),
        Path("docs/guides/operations.md"),
        Path("docs/reference/invariants.md"),
        Path("docs/reference/repository-layout.md"),
        Path("docs/status/current.md"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "Media Check" not in text, path
        assert "Media Auto Merge" not in text, path
