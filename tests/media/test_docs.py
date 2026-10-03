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
    for phrase in ['Never invent schema fields','Unknown is better than guessed','Do not persist ephemeral','Run full validation before commit','Normal data entry must not modify schemas']:
        assert phrase in agents


def test_living_docs_define_refresh_metadata_as_manual_bulk_maintenance():
    operations=Path('docs/guides/operations.md').read_text(encoding='utf-8')
    reference=Path('docs/reference/media-commands.md').read_text(encoding='utf-8')
    agents=Path('media/AGENTS.md').read_text(encoding='utf-8')
    for text in (operations, reference, agents):
        assert 'refresh_metadata' in text
    assert 'all_movies' in operations
    assert 'manual' in operations.lower() or 'вручную' in operations.lower()
    assert 'all_movies' in agents
    assert 'must not auto-merge' in agents.lower()


def test_living_docs_expose_v5_intelligence_operations_and_read_only_context():
    commands=Path('docs/reference/media-commands.md').read_text(encoding='utf-8')
    intelligence=Path('docs/architecture/intelligence.md').read_text(encoding='utf-8')
    pipeline=Path('docs/architecture/write-pipeline.md').read_text(encoding='utf-8')
    for operation in (
        'edit_viewing_feedback',
        'set_inferred_preferences',
        'set_semantic_fingerprint',
        'record_recommendation_interaction',
        'taste_context',
    ):
        assert operation in commands
    assert 'external discovery' in intelligence.lower()
    assert 'exact-head' in pipeline.lower()


def test_living_docs_expose_v51_similarity_assessment_and_current_read_model():
    model=Path('docs/architecture/media-model.md').read_text(encoding='utf-8')
    intelligence=Path('docs/architecture/intelligence.md').read_text(encoding='utf-8')
    commands=Path('docs/reference/media-commands.md').read_text(encoding='utf-8')
    web=Path('docs/architecture/web-and-broker.md').read_text(encoding='utf-8')
    status=Path('docs/status/current.md').read_text(encoding='utf-8')
    assert 'media/data/relations/similarity/' in model
    for operation in ('set_work_similarity','remove_work_similarity','assess_candidate'):
        assert operation in commands
    assert 'similarity' in intelligence.lower()
    assert 'не является preference' in intelligence
    assert 'не добав' in model and 'медиатек' in model
    assert 'Current manifest version: v3' in web
    assert 'Media Intelligence v5.1' in status
    assert 'assess_candidate' in status
    assert 'set_work_similarity' in status
    assert 'manifest v3' in status
