from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .common import iter_jsonl, iter_yaml_files, load_yaml
from .model import effective_metadata
from .validate import validate_repository

SCHEMA_SQL = r'''
PRAGMA foreign_keys=ON;
CREATE TABLE works (
  id TEXT PRIMARY KEY,
  format TEXT NOT NULL,
  medium TEXT,
  title_original TEXT NOT NULL,
  title_ru TEXT NOT NULL,
  year INTEGER,
  runtime_min INTEGER,
  original_language TEXT,
  production_status TEXT,
  synopsis_short TEXT,
  imdb_id TEXT UNIQUE,
  tmdb_media_type TEXT,
  tmdb_id INTEGER,
  external_provenance_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(tmdb_media_type, tmdb_id)
);
CREATE TABLE terms (term TEXT PRIMARY KEY, kind TEXT NOT NULL, label_ru TEXT NOT NULL, definition TEXT NOT NULL);
CREATE TABLE genres (work_id TEXT NOT NULL, term TEXT NOT NULL, PRIMARY KEY(work_id,term), FOREIGN KEY(work_id) REFERENCES works(id));
CREATE TABLE traits (work_id TEXT NOT NULL, term TEXT NOT NULL, source TEXT NOT NULL, confidence TEXT NOT NULL, FOREIGN KEY(work_id) REFERENCES works(id));
CREATE TABLE people_refs (work_id TEXT NOT NULL, role TEXT NOT NULL, position INTEGER NOT NULL, name TEXT NOT NULL, character TEXT, tmdb_id INTEGER, imdb_id TEXT, PRIMARY KEY(work_id,role,position), FOREIGN KEY(work_id) REFERENCES works(id));
CREATE TABLE external_metrics (work_id TEXT NOT NULL, provider TEXT NOT NULL, score REAL, votes INTEGER, observed_at TEXT, PRIMARY KEY(work_id,provider), FOREIGN KEY(work_id) REFERENCES works(id));
CREATE TABLE viewer_signals (entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, target TEXT NOT NULL, rating REAL, reaction TEXT, viewing TEXT, feedback_json TEXT, rewatch_intent TEXT, PRIMARY KEY(entity_type,entity_id,target));
CREATE TABLE group_signals (entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, target TEXT NOT NULL, rating REAL, reaction TEXT, feedback_json TEXT, suitability INTEGER, PRIMARY KEY(entity_type,entity_id,target));
CREATE TABLE seasons (work_id TEXT NOT NULL, number INTEGER NOT NULL, title TEXT, release_year INTEGER, episode_count INTEGER, PRIMARY KEY(work_id,number), FOREIGN KEY(work_id) REFERENCES works(id));
CREATE TABLE collections (id TEXT PRIMARY KEY, name_ru TEXT NOT NULL, name_original TEXT NOT NULL);
CREATE TABLE collection_members (collection_id TEXT NOT NULL, work_id TEXT NOT NULL, position INTEGER NOT NULL, PRIMARY KEY(collection_id,work_id), FOREIGN KEY(collection_id) REFERENCES collections(id), FOREIGN KEY(work_id) REFERENCES works(id));
CREATE TABLE lists (id TEXT PRIMARY KEY, target TEXT NOT NULL, title TEXT NOT NULL, description TEXT);
CREATE TABLE list_members (list_id TEXT NOT NULL, work_id TEXT NOT NULL, position INTEGER NOT NULL, PRIMARY KEY(list_id,work_id), FOREIGN KEY(list_id) REFERENCES lists(id), FOREIGN KEY(work_id) REFERENCES works(id));
CREATE TABLE interactions (id TEXT PRIMARY KEY, at TEXT NOT NULL, target TEXT NOT NULL, type TEXT NOT NULL, work_id TEXT, list_id TEXT, reason TEXT);
CREATE TABLE relations (entity_id TEXT NOT NULL, source_target TEXT, relation_kind TEXT NOT NULL, type TEXT NOT NULL, target_id TEXT NOT NULL, strength INTEGER, dimensions_json TEXT, note TEXT, source TEXT, confidence TEXT);
CREATE TABLE target_states (entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, target TEXT NOT NULL, interest_state TEXT, interest_priority INTEGER, PRIMARY KEY(entity_type,entity_id,target));
'''


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _signal_rows(con: sqlite3.Connection, entity_type: str, entity: dict[str, Any]) -> None:
    eid=entity['id']
    for target, signal in sorted((entity.get('viewer_signals') or {}).items()):
        con.execute('INSERT INTO viewer_signals VALUES (?,?,?,?,?,?,?,?)',(
            entity_type,eid,target,(signal.get('rating') or {}).get('score'),(signal.get('reaction') or {}).get('value'),
            (signal.get('viewing') or {}).get('status'),_json(signal.get('feedback')),(signal.get('rewatch') or {}).get('intent')))
        for rel in signal.get('relations') or []:
            con.execute('INSERT INTO relations VALUES (?,?,?,?,?,?,?,?,?,?)',(eid,target,'viewer',rel.get('type'),rel.get('target_id'),rel.get('strength'),_json(rel.get('dimensions') or []),rel.get('note'),rel.get('source'),rel.get('confidence')))
    for target, signal in sorted((entity.get('group_signals') or {}).items()):
        con.execute('INSERT INTO group_signals VALUES (?,?,?,?,?,?,?)',(
            entity_type,eid,target,(signal.get('rating') or {}).get('score'),(signal.get('reaction') or {}).get('value'),
            _json(signal.get('feedback')),(signal.get('suitability') or {}).get('strength')))
        for rel in signal.get('relations') or []:
            con.execute('INSERT INTO relations VALUES (?,?,?,?,?,?,?,?,?,?)',(eid,target,'group',rel.get('type'),rel.get('target_id'),rel.get('strength'),_json(rel.get('dimensions') or []),rel.get('note'),rel.get('source'),rel.get('confidence')))
    for target,state in sorted((entity.get('target_states') or {}).items()):
        interest=(state or {}).get('interest') or {}
        con.execute('INSERT INTO target_states VALUES (?,?,?,?,?)',(entity_type,eid,target,interest.get('state'),interest.get('priority')))


def _populate(con: sqlite3.Connection, media_root: Path) -> None:
    vocabulary=load_yaml(media_root/'vocabulary.yaml') or {}
    for term,meta in sorted((vocabulary.get('terms') or {}).items()):
        con.execute('INSERT INTO terms VALUES (?,?,?,?)',(term,meta.get('kind'),meta.get('label_ru'),meta.get('definition')))

    for path in iter_yaml_files(media_root/'data/works'):
        work=load_yaml(path) or {}; ident=work.get('identity') or {}; meta=effective_metadata(work)
        external=(work.get('metadata') or {}).get('external') or {}; ext_ids=ident.get('external_ids') or {}; tmdb=ext_ids.get('tmdb') or {}
        con.execute('INSERT INTO works VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
            work['id'],ident.get('format'),ident.get('medium'),ident.get('title_original'),ident.get('title_ru'),ident.get('year'),
            meta.get('runtime_min'),meta.get('original_language'),meta.get('production_status'),meta.get('synopsis_short'),ext_ids.get('imdb'),
            tmdb.get('media_type'),tmdb.get('id'),_json(external.get('provenance'))))
        for term in sorted(meta.get('genres') or []): con.execute('INSERT INTO genres VALUES (?,?)',(work['id'],term))
        for trait in ((work.get('metadata') or {}).get('semantic') or {}).get('traits') or []:
            con.execute('INSERT INTO traits VALUES (?,?,?,?)',(work['id'],trait.get('term'),trait.get('source'),trait.get('confidence')))
        for role,key in [('director','directors'),('writer','writers'),('cast','main_cast')]:
            for pos,person in enumerate(meta.get(key) or []):
                ids=person.get('external_ids') or {}
                con.execute('INSERT INTO people_refs VALUES (?,?,?,?,?,?,?)',(work['id'],role,pos,person.get('name'),person.get('character'),ids.get('tmdb'),ids.get('imdb')))
        for provider,metric in sorted((external.get('external_metrics') or {}).items()):
            con.execute('INSERT INTO external_metrics VALUES (?,?,?,?,?)',(work['id'],provider,metric.get('score'),metric.get('votes'),metric.get('observed_at')))
        for season in work.get('seasons') or []:
            con.execute('INSERT INTO seasons VALUES (?,?,?,?,?)',(work['id'],season.get('number'),season.get('title'),season.get('release_year'),season.get('episode_count')))
        for rel in work.get('canonical_relations') or []:
            con.execute('INSERT INTO relations VALUES (?,?,?,?,?,?,?,?,?,?)',(work['id'],None,'canonical',rel.get('type'),rel.get('target_id'),None,'[]',None,rel.get('source'),None))
        _signal_rows(con,'work',work)

    for path in iter_yaml_files(media_root/'data/collections'):
        col=load_yaml(path) or {}
        con.execute('INSERT INTO collections VALUES (?,?,?)',(col['id'],col.get('name_ru'),col.get('name_original')))
        for pos,member in enumerate(col.get('member_ids') or []): con.execute('INSERT INTO collection_members VALUES (?,?,?)',(col['id'],member,pos))
        _signal_rows(con,'collection',col)

    for path in iter_yaml_files(media_root/'data/lists'):
        doc=load_yaml(path) or {}
        con.execute('INSERT INTO lists VALUES (?,?,?,?)',(doc['id'],doc.get('target'),doc.get('title'),doc.get('description')))
        for pos,member in enumerate(doc.get('member_ids') or []): con.execute('INSERT INTO list_members VALUES (?,?,?)',(doc['id'],member,pos))

    idir=media_root/'data/interactions'
    if idir.exists():
        for path in sorted(idir.glob('*.jsonl')):
            for _,event in iter_jsonl(path):
                con.execute('INSERT INTO interactions VALUES (?,?,?,?,?,?,?)',(event.get('id'),event.get('at'),event.get('target'),event.get('type'),event.get('work_id'),event.get('list_id'),event.get('reason')))


def build_database(media_root: Path, output: Path | None = None) -> Path:
    media_root=Path(media_root)
    issues=validate_repository(media_root.parent)
    if issues:
        text='; '.join(f'{i.code}: {i.message}' for i in issues[:10])
        raise ValueError(f'canonical validation failed: {text}')
    output=Path(output) if output else media_root/'generated/database.sqlite'
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp=output.with_name(output.name+'.tmp')
    if tmp.exists(): tmp.unlink()
    try:
        con=sqlite3.connect(tmp)
        try:
            con.executescript(SCHEMA_SQL)
            _populate(con,media_root)
            con.commit()
        finally:
            con.close()
        os.replace(tmp,output)
    except Exception:
        if tmp.exists(): tmp.unlink()
        raise
    return output


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description='Build derived SQLite media database')
    parser.add_argument('media_root',nargs='?',default='media')
    parser.add_argument('--output')
    args=parser.parse_args(argv)
    print(build_database(Path(args.media_root),Path(args.output) if args.output else None))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
