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
