from __future__ import annotations

from pathlib import Path
from typing import Any

from media.domain.commands import TasteContextRequest
from media.domain.errors import UnknownTargetError
from media.repository.index_repo import IndexRepository
from media.repository.yaml_repo import YamlRepository
from media.service.similarity import similarity_context
from media.tools.build_profiles import build_profile

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "none": 0}


def _title(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title_original": row.get("title_original"),
        "title_ru": row.get("title_ru"),
        "year": row.get("year"),
    }


def _strongest_affinities(profile: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    rows=[]
    for term, affinity in (profile.get("affinities") or {}).items():
        rows.append({
            "term": term,
            "score": affinity.get("score", 0),
            "confidence": affinity.get("confidence", "low"),
            "evidence_count": affinity.get("evidence_count", 0),
            "evidence": list((affinity.get("evidence") or [])[:5]),
        })
    rows.sort(key=lambda item: (-_CONFIDENCE_RANK.get(item["confidence"],0), -abs(float(item["score"])), item["term"]))
    return rows[:limit]


def _rated_item(row: dict[str, Any], ratings: dict[str, float]) -> dict[str, Any]:
    result=_title(row); result["ratings"]={key:ratings[key] for key in sorted(ratings)}; result["traits"]=list(row.get("traits") or [])
    return result


def _feedback_rows(repo: YamlRepository, target: str, members: list[str], limit: int) -> list[dict[str, Any]]:
    rows=[]
    for record in repo.iter_works():
        data=record.data; ident=data.get("identity") or {}; updated=(data.get("provenance") or {}).get("updated_at") or ""
        signals=[]
        if members:
            for member in members:
                signal=(data.get("viewer_signals") or {}).get(member) or {}
                feedback=signal.get("feedback") or {}
                if feedback.get("summary") or feedback.get("signals"):
                    signals.append((member,feedback))
            direct=(data.get("group_signals") or {}).get(target) or {}; feedback=direct.get("feedback") or {}
            if feedback.get("summary") or feedback.get("signals"): signals.append((target,feedback))
        else:
            signal=(data.get("viewer_signals") or {}).get(target) or {}; feedback=signal.get("feedback") or {}
            if feedback.get("summary") or feedback.get("signals"): signals.append((target,feedback))
        for source_target,feedback in signals:
            rows.append({
                "id": record.id,
                "title_original": ident.get("title_original"),
                "title_ru": ident.get("title_ru"),
                "year": ident.get("year"),
                "source_target": source_target,
                "updated_at": updated,
                "summary": feedback.get("summary"),
                "signals": list(feedback.get("signals") or []),
            })
    rows.sort(key=lambda item: (str(item.get("updated_at") or ""), item["id"], item["source_target"]), reverse=True)
    return rows[:limit]


def build_taste_context(media_root: Path, request: TasteContextRequest) -> dict[str, Any]:
    media_root=Path(media_root); repo=YamlRepository(media_root); viewers,groups=repo.configured_targets()
    if request.target not in viewers and request.target not in groups:
        raise UnknownTargetError(f"unknown target: {request.target}")
    members=list(groups.get(request.target, [])); profile=build_profile(media_root, request.target)
    rows=IndexRepository(media_root/"generated"/"index.jsonl").rows()
    high=[]; low=[]; watched=[]; not_interested=[]; agreements=[]; disagreements=[]
    for row in rows:
        interest=(row.get("interest") or {}).get(request.target) or {}
        if interest.get("state")=="not_interested": not_interested.append(row["id"])
        if not members:
            signal=(row.get("viewer") or {}).get(request.target) or {}
            if signal.get("viewing")=="watched": watched.append(row["id"])
            rating=signal.get("rating")
            if isinstance(rating,(int,float)):
                item=_rated_item(row,{request.target:float(rating)})
                if float(rating)>=7: high.append((float(rating),row["id"],item))
                if float(rating)<=4: low.append((float(rating),row["id"],item))
        else:
            viewer=row.get("viewer") or {}
            if members and all((viewer.get(member) or {}).get("viewing")=="watched" for member in members): watched.append(row["id"])
            ratings={member:float((viewer.get(member) or {})["rating"]) for member in members if isinstance((viewer.get(member) or {}).get("rating"),(int,float))}
            if ratings:
                values=list(ratings.values())
                if len(values)>=2:
                    item=_rated_item(row,ratings)
                    if all(value>=7 for value in values):
                        agreements.append({**item,"direction":"positive"}); high.append((min(values),row["id"],item))
                    elif all(value<=4 for value in values):
                        agreements.append({**item,"direction":"negative"}); low.append((max(values),row["id"],item))
                    if max(values)-min(values)>=2.5 or (min(values)<=4 and max(values)>=7): disagreements.append(item)
                elif len(values)==1:
                    only=values[0]; item=_rated_item(row,ratings)
                    if only>=7: high.append((only,row["id"],item))
                    if only<=4: low.append((only,row["id"],item))
            group_rating=((row.get("groups") or {}).get(request.target) or {}).get("rating")
            if isinstance(group_rating,(int,float)) and not ratings:
                item=_rated_item(row,{request.target:float(group_rating)})
                if float(group_rating)>=7: high.append((float(group_rating),row["id"],item))
                if float(group_rating)<=4: low.append((float(group_rating),row["id"],item))
    high.sort(key=lambda item:(-item[0],item[1])); low.sort(key=lambda item:(item[0],item[1]))
    result={
        "schema_version":1,
        "target":request.target,
        "profile":{
            "explicit_preferences":list(profile.get("explicit_preferences") or []),
            "inferred_preferences":list(profile.get("inferred_preferences") or []),
            "rules":list(profile.get("rules") or []),
            "constraints":list(profile.get("constraints") or []),
            "strongest_affinities":_strongest_affinities(profile),
            "summary":dict(profile.get("summary") or {}),
        },
        "representative":{
            "high":[item[2] for item in high[:request.representative_limit]],
            "low":[item[2] for item in low[:request.representative_limit]],
        },
        "recent_feedback":_feedback_rows(repo,request.target,members,request.recent_limit),
        "similarities":similarity_context(media_root,request.target),
        "exclusions":{"watched":sorted(watched),"not_interested":sorted(not_interested)},
    }
    if members:
        agreements.sort(key=lambda item:item["id"]); disagreements.sort(key=lambda item:item["id"])
        result["couple"]={"members":members,"agreements":agreements[:20],"disagreements":disagreements[:20]}
    return result
