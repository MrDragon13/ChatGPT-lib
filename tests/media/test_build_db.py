from pathlib import Path
import shutil
import sqlite3

import pytest

from media.tools.build_db import build_database
from media.tools.common import dump_yaml


def seed(tmp_path: Path) -> Path:
    root=tmp_path/'repo'; media=root/'media'
    for d in ['data/works','data/collections','data/lists','data/interactions','data/tombstones','preferences/explicit','config','generated']:
        (media/d).mkdir(parents=True,exist_ok=True)
    shutil.copytree(Path('media/schemas'),media/'schemas')
    shutil.copy(Path('media/vocabulary.yaml'),media/'vocabulary.yaml')
    shutil.copy(Path('media/config/viewers.yaml'),media/'config/viewers.yaml')
    shutil.copy(Path('media/config/groups.yaml'),media/'config/groups.yaml')
    shutil.copy(Path('media/preferences/explicit/primary.yaml'),media/'preferences/explicit/primary.yaml')
    dump_yaml(media/'data/works/a.yaml',{
      'schema_version':4,'id':'a','entity_type':'work','identity':{'format':'movie','title_original':'A','title_ru':'A','year':2020,'external_ids':{'tmdb':{'media_type':'movie','id':123},'imdb':'tt1234567'}},
      'metadata':{'external':{'genres':['genre.drama'],'runtime_min':100,'directors':[{'name':'D','external_ids':{'tmdb':9}}],'external_metrics':{'imdb':{'score':8.1,'votes':100,'observed_at':'2026-10-01'}},'provenance':{'provider':'tmdb','provider_id':123,'fetched_at':'2026-10-01'}},'overrides':{'runtime_min':105},'semantic':{'traits':[{'term':'story.intrigue','source':'llm_inferred','confidence':'medium'}]}},
      'viewer_signals':{'primary':{'rating':{'score':8.5,'source':'explicit','confidence':'exact'},'reaction':{'value':'liked','source':'explicit','confidence':'high'}}},
      'target_states':{'primary':{'interest':{'state':'shortlist','priority':4}}}
    })
    dump_yaml(media/'data/works/s.yaml',{'schema_version':4,'id':'s','entity_type':'work','identity':{'format':'series','title_original':'S','title_ru':'S','year':2021,'external_ids':{'tmdb':{'media_type':'tv','id':123}}},'seasons':[{'number':0,'title':'Specials'}]})
    dump_yaml(media/'data/collections/c.yaml',{'schema_version':4,'id':'c','entity_type':'collection','name_ru':'C','name_original':'C','member_ids':['a']})
    dump_yaml(media/'data/lists/l.yaml',{'schema_version':4,'id':'l','entity_type':'list','target':'primary','title':'L','member_ids':['a']})
    return media


def scalar(db:Path,sql:str,params=()):
    with sqlite3.connect(db) as con:
        return con.execute(sql,params).fetchone()[0]


def test_build_database_rebuilds_expected_core_tables_and_uses_effective_metadata(tmp_path: Path):
    media=seed(tmp_path); db=build_database(media)
    assert scalar(db,'select count(*) from works')==2
    assert scalar(db,'select runtime_min from works where id=?',('a',))==105
    assert scalar(db,'select count(*) from genres')==1
    assert scalar(db,'select count(*) from traits')==1
    assert scalar(db,'select count(*) from people_refs')==1
    assert scalar(db,'select count(*) from seasons')==1
    assert scalar(db,'select count(*) from collections')==1
    assert scalar(db,'select count(*) from collection_members')==1
    assert scalar(db,'select count(*) from lists')==1
    assert scalar(db,'select count(*) from list_members')==1
    assert scalar(db,'select count(*) from viewer_signals')==1
    assert scalar(db,'select count(*) from target_states')==1


def test_tmdb_movie_tv_same_numeric_id_coexist_and_duplicate_composite_fails(tmp_path: Path):
    media=seed(tmp_path)
    build_database(media)
    dump_yaml(media/'data/works/b.yaml',{'schema_version':4,'id':'b','entity_type':'work','identity':{'format':'movie','title_original':'B','title_ru':'B','year':2022,'external_ids':{'tmdb':{'media_type':'movie','id':123}}}})
    with pytest.raises(ValueError,match='duplicate_tmdb'):
        build_database(media)


def test_external_metric_observed_at_and_provider_provenance_are_preserved(tmp_path: Path):
    media=seed(tmp_path); db=build_database(media)
    with sqlite3.connect(db) as con:
        metric=con.execute("select score,votes,observed_at from external_metrics where work_id='a' and provider='imdb'").fetchone()
        provenance=con.execute("select external_provenance_json from works where id='a'").fetchone()[0]
    assert metric==(8.1,100,'2026-10-01')
    assert 'tmdb' in provenance and '123' in provenance


def test_rebuild_is_deterministic_in_row_content(tmp_path: Path):
    media=seed(tmp_path); db=build_database(media)
    with sqlite3.connect(db) as con:
        first=con.execute('select id,title_ru,runtime_min from works order by id').fetchall()
    build_database(media,db)
    with sqlite3.connect(db) as con:
        second=con.execute('select id,title_ru,runtime_min from works order by id').fetchall()
    assert second==first
