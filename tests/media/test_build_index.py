from pathlib import Path

from media.domain.digests import compute_viewer_digest
from media.tools.build_index import build_index_rows, write_index
from media.tools.common import dump_yaml, iter_jsonl, load_yaml


def work(work_id, year=2020):
    return {
        'schema_version': 4,
        'id': work_id,
        'entity_type': 'work',
        'identity': {'format': 'movie', 'title_original': work_id, 'title_ru': work_id, 'year': year},
    }


def seed(tmp_path: Path) -> Path:
    media = tmp_path / 'media'
    for d in ['data/works', 'data/collections', 'data/tombstones', 'config', 'generated']:
        (media / d).mkdir(parents=True, exist_ok=True)
    dump_yaml(media / 'config/viewers.yaml', {'schema_version':4,'viewers':{'primary':{},'partner':{}}})
    dump_yaml(media / 'config/groups.yaml', {'schema_version':4,'groups':{'couple':{'members':['primary','partner']}}})
    a = work('a-2020')
    a['metadata'] = {
        'external': {'genres': ['genre.drama'], 'runtime_min': 100},
        'overrides': {'runtime_min': 105},
        'semantic': {'traits': [{'term': 'story.intrigue', 'source': 'llm_inferred', 'confidence': 'medium'}]},
    }
    a['viewer_signals'] = {
        'primary': {'rating': {'score': 8.5, 'source': 'explicit', 'confidence': 'exact'}, 'reaction': {'value': 'liked', 'source': 'explicit', 'confidence': 'high'}},
        'partner': {'reaction': {'value': 'liked', 'source': 'explicit', 'confidence': 'high'}},
    }
    a['group_signals'] = {'couple': {'reaction': {'value': 'liked', 'source': 'explicit', 'confidence': 'high'}}}
    a['target_states'] = {'primary': {'interest': {'state': 'shortlist', 'priority': 4}}}
    dump_yaml(media / 'data/works/a-2020.yaml', a)
    dump_yaml(media / 'data/works/b-2021.yaml', work('b-2021', 2021))
    dump_yaml(media / 'data/collections/c1.yaml', {'schema_version':4,'id':'c1','entity_type':'collection','name_ru':'C1','name_original':'C1','member_ids':['a-2020']})
    dump_yaml(media / 'data/tombstones/old.yaml', {'schema_version':4,'id':'old','entity_type':'tombstone','status':'merged','redirect_to':'a-2020'})
    return media


def test_build_index_rows_are_sorted_compact_and_effective_metadata_uses_override(tmp_path: Path):
    media = seed(tmp_path)
    rows = build_index_rows(media)
    assert [r['id'] for r in rows] == ['a-2020', 'b-2021']
    a = rows[0]
    assert a['runtime_min'] == 105
    assert a['genres'] == ['genre.drama']
    assert a['traits'] == ['story.intrigue']
    assert a['viewer']['primary'] == {'rating': 8.5, 'reaction': 'liked'}
    assert a['viewer']['partner'] == {'reaction': 'liked'}
    assert a['groups']['couple'] == {'reaction': 'liked'}
    assert a['interest']['primary'] == {'state': 'shortlist', 'priority': 4}
    assert a['collections'] == ['c1']
    assert 'old' not in {r['id'] for r in rows}


def test_identity_fields_are_not_shadowed_by_metadata_overrides(tmp_path: Path):
    media = seed(tmp_path)
    p = media / 'data/works/a-2020.yaml'
    import yaml
    d = yaml.safe_load(p.read_text(encoding='utf-8'))
    d['metadata']['overrides']['title_ru'] = 'Should not be allowed by schema, but index must still use identity'
    dump_yaml(p, d)
    row = build_index_rows(media)[0]
    assert row['title_ru'] == 'a-2020'


def test_write_index_is_deterministic_jsonl(tmp_path: Path):
    media = seed(tmp_path)
    out = media / 'generated/index.jsonl'
    write_index(media, out)
    first = out.read_bytes()
    write_index(media, out)
    assert out.read_bytes() == first
    assert [row['id'] for _, row in iter_jsonl(out)] == ['a-2020', 'b-2021']


def test_index_exposes_digest_for_every_configured_target_even_when_signal_is_absent(tmp_path: Path):
    media = seed(tmp_path)
    rows = {row["id"]: row for row in build_index_rows(media)}
    a_doc = load_yaml(media / "data/works/a-2020.yaml")
    b_doc = load_yaml(media / "data/works/b-2021.yaml")

    assert set(rows["a-2020"]["viewer_digests"]) == {"primary", "partner", "couple"}
    for target in ("primary", "partner", "couple"):
        assert rows["a-2020"]["viewer_digests"][target] == compute_viewer_digest(a_doc, target)
        assert rows["b-2021"]["viewer_digests"][target] == compute_viewer_digest(b_doc, target)
