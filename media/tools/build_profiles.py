from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .common import dump_yaml, iter_jsonl, iter_yaml_files, load_yaml

CONFIDENCE_WEIGHT = {'exact':1.0,'high':0.9,'medium':0.7,'low':0.5,'none':0.25}
SOURCE_WEIGHT = {'explicit':1.0,'inferred':0.7}
SENTIMENT_SIGN = {'positive':1.0,'negative':-1.0,'mixed':0.0,'neutral':0.0}


def _entities(media_root: Path) -> Iterable[dict[str, Any]]:
    for directory in ['data/works','data/collections']:
        for path in iter_yaml_files(media_root/directory):
            doc=load_yaml(path)
            if isinstance(doc,dict): yield doc


def _configured(media_root: Path) -> tuple[set[str], dict[str,list[str]]]:
    viewers=set((load_yaml(media_root/'config/viewers.yaml') or {}).get('viewers',{}))
    groups_doc=(load_yaml(media_root/'config/groups.yaml') or {}).get('groups',{})
    groups={gid:list((meta or {}).get('members',[])) for gid,meta in groups_doc.items()}
    return viewers,groups


def _explicit(media_root: Path,target:str)->dict[str,Any]:
    path=media_root/f'preferences/explicit/{target}.yaml'
    if not path.exists(): return {'preferences':[],'rules':[],'constraints':[]}
    doc=load_yaml(path) or {}
    return {k:list(doc.get(k) or []) for k in ['preferences','rules','constraints']}


def _add_feedback(bucket:dict[str,list[dict[str,Any]]], entity_id:str, source_target:str, signal:dict[str,Any], source_kind:str='feedback')->None:
    feedback=signal.get('feedback') or {}
    for item in feedback.get('signals') or []:
        term=item.get('term')
        if not term: continue
        strength=int(item.get('strength') or 1); src=item.get('source','inferred'); conf=item.get('confidence','medium'); sign=SENTIMENT_SIGN.get(item.get('sentiment'),0.0)
        weight=strength*SOURCE_WEIGHT.get(src,0.7)*CONFIDENCE_WEIGHT.get(conf,0.7)
        bucket[term].append({'entity_id':entity_id,'source_target':source_target,'source_kind':source_kind,'sentiment':item.get('sentiment'),'strength':strength,'source':src,'confidence':conf,'signed':sign*weight,'weight':weight})


def _add_explicit(bucket:dict[str,list[dict[str,Any]]], prefs:list[dict[str,Any]],target:str)->None:
    for item in prefs:
        term=item.get('term')
        if not term or item.get('affinity') is None: continue
        conf=item.get('confidence','high'); weight=3.0*CONFIDENCE_WEIGHT.get(conf,0.9); affinity=float(item['affinity'])
        bucket[term].append({'entity_id':None,'source_target':target,'source_kind':'explicit_preference','sentiment':None,'strength':3,'source':'explicit','confidence':conf,'signed':affinity*weight,'weight':weight,'preference_id':item.get('id')})


def _add_signal_summary(summary:dict[str,int], signal:dict[str,Any])->None:
    if (signal.get('rating') or {}).get('score') is not None: summary['ratings_count']+=1
    if (signal.get('reaction') or {}).get('value') is not None: summary['reactions_count']+=1
    if (signal.get('viewing') or {}).get('status') is not None: summary['viewing_count']+=1
    if signal.get('rewatch'): summary['rewatch_count']+=1
    summary['relations_count']+=len(signal.get('relations') or [])


def _interaction_counts(media_root:Path,target:str)->dict[str,int]:
    counts=defaultdict(int); idir=media_root/'data/interactions'
    if idir.exists():
        for path in sorted(idir.glob('*.jsonl')):
            for _,event in iter_jsonl(path):
                if event.get('target')==target: counts[f"{event.get('type')}_count"]+=1
    return dict(counts)


def build_profile(media_root: Path, target: str) -> dict[str, Any]:
    viewers,groups=_configured(media_root)
    if target not in viewers and target not in groups: raise ValueError(f'unknown target: {target}')
    members=groups.get(target,[]); evidence=defaultdict(list); summary=defaultdict(int)
    for entity in _entities(media_root):
        eid=entity.get('id'); viewer_signals=entity.get('viewer_signals') or {}; group_signals=entity.get('group_signals') or {}
        if target in viewers:
            sig=viewer_signals.get(target)
            if sig:
                _add_feedback(evidence,eid,target,sig)
                _add_signal_summary(summary,sig)
        else:
            for member in members:
                sig=viewer_signals.get(member)
                if sig:
                    _add_feedback(evidence,eid,member,sig)
                    _add_signal_summary(summary,sig)
            direct=group_signals.get(target)
            if direct:
                _add_feedback(evidence,eid,target,direct,source_kind='group_feedback')
                _add_signal_summary(summary,direct)
    explicit=_explicit(media_root,target); _add_explicit(evidence,explicit['preferences'],target)
    affinities={}
    for term,items in sorted(evidence.items()):
        total=sum(x['weight'] for x in items); signed=sum(x['signed'] for x in items); score=0.0 if total==0 else signed/total
        public=[]
        for x in items:
            y={k:v for k,v in x.items() if k not in {'signed','weight'}}; y['weight']=round(x['weight'],6); public.append(y)
        abs_weight=sum(abs(x['weight']) for x in items); confidence='high' if abs_weight>=5 else ('medium' if abs_weight>=2 else 'low')
        affinities[term]={'score':round(score,6),'confidence':confidence,'evidence_count':len(items),'evidence':public}
    summary.update(_interaction_counts(media_root,target))
    return {'schema_version':4,'target':target,'generated_from':'canonical-v4','affinities':affinities,'explicit_preferences':explicit['preferences'],'rules':explicit['rules'],'constraints':explicit['constraints'],'summary':dict(sorted(summary.items())),'evidence':{'entity_count':sum(1 for _ in _entities(media_root))}}


def write_profiles(media_root:Path, output_dir:Path|None=None)->list[Path]:
    viewers,groups=_configured(media_root); targets=sorted(viewers|set(groups)); outdir=Path(output_dir) if output_dir is not None else media_root/'generated/profiles'; outdir.mkdir(parents=True,exist_ok=True); paths=[]
    for target in targets:
        p=outdir/f'{target}.yaml'; dump_yaml(p,build_profile(media_root,target)); paths.append(p)
    return paths


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description='Build derived media taste profiles'); parser.add_argument('media_root',nargs='?',default='media'); args=parser.parse_args(argv)
    for path in write_profiles(Path(args.media_root)): print(path)
    return 0


if __name__=='__main__': raise SystemExit(main())
