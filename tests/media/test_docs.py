from pathlib import Path

import json

from media.tools.common import load_yaml


def test_operational_docs_and_core_paths_exist():
    required=[
        'media/AGENTS.md','media/README.md','media/.gitignore','media/vocabulary.yaml',
        'media/config/viewers.yaml','media/config/groups.yaml','media/tools/validate.py',
        'media/tools/build_index.py','media/tools/build_profiles.py','media/tools/build_db.py',
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


def test_readme_commands_match_real_modules_and_agents_contract_mentions_guardrails():
    readme=Path('media/README.md').read_text(encoding='utf-8')
    for cmd in ['python -m media.tools.validate .','python -m media.tools.build_index media','python -m media.tools.build_profiles media','python -m media.tools.build_db media']:
        assert cmd in readme
    agents=Path('media/AGENTS.md').read_text(encoding='utf-8')
    for phrase in ['Never invent schema fields','Unknown is better than guessed','Do not persist ephemeral','Run full validation before commit','Normal data entry must not modify schemas']:
        assert phrase in agents


def test_docs_define_refresh_metadata_as_manual_bulk_maintenance():
    readme=Path('media/README.md').read_text(encoding='utf-8')
    agents=Path('media/AGENTS.md').read_text(encoding='utf-8')
    assert 'refresh_metadata' in readme
    assert 'all_movies' in readme
    assert 'manual' in readme.lower() or 'вручную' in readme.lower()
    assert 'refresh_metadata' in agents
    assert 'all_movies' in agents
    assert 'must not auto-merge' in agents.lower()


def test_v5_docs_expose_intelligence_commands_and_read_only_context():
    readme=Path('media/README.md').read_text(encoding='utf-8')
    assert 'Personal Media Library v5' in readme
    for operation in (
        'edit_viewing_feedback',
        'set_inferred_preferences',
        'set_semantic_fingerprint',
        'record_recommendation_interaction',
    ):
        assert operation in readme
    assert 'python -m media.cli taste-context' in readme
    assert 'external discovery' in readme.lower()
    assert 'dispatch-only' in readme.lower()


def test_v51_docs_expose_similarity_assessment_and_current_read_model():
    readme=Path('media/README.md').read_text(encoding='utf-8')
    status=Path('media/V5_STATUS.md').read_text(encoding='utf-8')
    for phrase in (
        'data/relations/similarity/',
        'set_work_similarity',
        'remove_work_similarity',
        'assess_candidate',
        'python -m media.cli assess-candidate',
        'manifest v3',
    ):
        assert phrase in readme
    assert 'similarity' in readme.lower()
    assert 'не является preference сама по себе' in readme
    assert 'не создаёт canonical work' in readme
    assert 'Media Intelligence v5.1' in status
    assert 'Task 1–4' in status
    assert 'assess_candidate' in status
    assert 'set_work_similarity' in status
    assert 'manifest v3' in status
