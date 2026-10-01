from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

import media.service.transaction as transaction
from media.commands.schema import parse_command
from media.domain.errors import PathPolicyError
from media.providers.tmdb import TMDBProvider
from media.repository.sqlite_repo import SQLiteRepository
from media.service.path_policy import verify_changed_paths
from media.service.transaction import execute_command
from tests.media.fixture_repo import copy_fixture_repo


def test_sqlite_adapter_matches_real_build_db_works_columns(tmp_path):
    db=tmp_path/'database.sqlite'; con=sqlite3.connect(db)
    try:
        con.execute("CREATE TABLE works (id TEXT PRIMARY KEY, format TEXT NOT NULL, medium TEXT, title_original TEXT NOT NULL, title_ru TEXT NOT NULL, year INTEGER, runtime_min INTEGER, original_language TEXT, production_status TEXT, synopsis_short TEXT, imdb_id TEXT UNIQUE, tmdb_media_type TEXT, tmdb_id INTEGER, external_provenance_json TEXT NOT NULL DEFAULT '{}')")
        con.executemany("INSERT INTO works (id,format,title_original,title_ru,year,runtime_min) VALUES (?,?,?,?,?,?)", [('dune-1984','movie','Dune','Дюна',1984,137),('dune-2021','movie','Dune','Дюна',2021,155)])
        con.commit()
    finally:
        con.close()
    assert [row['id'] for row in SQLiteRepository(db).search('dune')]==['dune-1984','dune-2021']


def test_path_allowlist_rejects_nested_work_path():
    with pytest.raises(PathPolicyError):
        verify_changed_paths('record_viewing_feedback',['media/data/works/nested/evil.yaml'])


def test_receipt_copy_failure_rolls_back_media_files(tmp_path,monkeypatch):
    root=copy_fixture_repo(tmp_path); before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}; original=shutil.copy2
    def fail_receipt(src,dst,*args,**kwargs):
        if '.media/operations/' in str(dst).replace('\\','/'):
            raise OSError('receipt storage unavailable')
        return original(src,dst,*args,**kwargs)
    monkeypatch.setattr(transaction.shutil,'copy2',fail_receipt)
    command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174399','operation':'record_viewing_feedback','work_ref':{'id':'arrival-2016'},'target_updates':[{'target':'primary','viewing':{'status':'partial'}}]})
    with pytest.raises(OSError,match='receipt storage unavailable'):
        execute_command(root,command,now=datetime(2026,10,1,tzinfo=timezone.utc))
    after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert after==before


def test_tmdb_genres_are_canonical_vocabulary_ids():
    fixture=Path(__file__).parents[1]/'fixtures/tmdb/movie_arrival.json'; payload=json.loads(fixture.read_text(encoding='utf-8'))
    def request_json(url,headers):
        return payload
    metadata=TMDBProvider('token',request_json=request_json).fetch_work('movie',329865)
    assert metadata.external['genres']==['genre.science_fiction','genre.drama']


def test_workflow_exposes_tmdb_secret_only_to_add_work_step():
    text=(Path(__file__).parents[2]/'.github/workflows/media-command.yml').read_text(encoding='utf-8')
    assert 'Apply command without provider secret' in text
    assert "steps.operation.outputs.operation != 'add_work'" in text
    assert 'Apply add-work command with TMDB secret' in text
    assert "steps.operation.outputs.operation == 'add_work'" in text
    assert text.count('TMDB_READ_TOKEN: ${{ secrets.TMDB_READ_TOKEN }}')==1
