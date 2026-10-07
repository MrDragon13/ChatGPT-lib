from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

import yaml

from media.tools.common import load_yaml


VIEWING_LABELS = {
    "unwatched": "не просмотрено",
    "watched": "просмотрено",
    "partial": "частично просмотрено",
    "dropped": "брошено",
    "forgotten": "просмотрено, детали забыты",
}

REACTION_LABELS = {
    "liked": "понравилось",
    "disliked": "не понравилось",
    "neutral": "нейтрально",
    "mixed": "смешанное впечатление",
}

SENTIMENT_LABELS = {
    "positive": "положительно",
    "negative": "отрицательно",
    "mixed": "смешанно",
    "neutral": "нейтрально",
}


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value=value.strip()
    return value or None


def _display_title(identity: Mapping[str, Any]) -> str:
    ru=_text(identity.get("title_ru"))
    original=_text(identity.get("title_original"))
    if ru and original and ru.casefold()!=original.casefold():
        return f"{ru} / {original}"
    return ru or original or "Без названия"


def _work_heading(work: Mapping[str, Any]) -> str:
    identity=work.get("identity") or {}
    title=_display_title(identity)
    year=identity.get("year")
    return f"{title} ({year})" if year is not None else title


def _sort_key(work: Mapping[str, Any]) -> tuple[str, int, str]:
    identity=work.get("identity") or {}
    title=_display_title(identity).casefold()
    year=identity.get("year")
    normalized_year=int(year) if isinstance(year, int) else 9999
    return (title, normalized_year, str(work.get("id") or ""))


def _format_score(score: Any) -> str:
    if isinstance(score, float) and score.is_integer():
        return str(int(score))
    return str(score)


def _viewer_lines(signal: Mapping[str, Any]) -> list[str]:
    lines: list[str]=[]

    viewing=signal.get("viewing")
    if isinstance(viewing, Mapping):
        status=viewing.get("status")
        if status in VIEWING_LABELS:
            value=VIEWING_LABELS[status]
            times=viewing.get("times_watched")
            if isinstance(times, int) and times > 0:
                prefix="≈" if viewing.get("times_watched_approximate") else ""
                value += f"; просмотров: {prefix}{times}"
            lines.append(f"- Просмотр: {value}")

    rating=signal.get("rating")
    if isinstance(rating, Mapping):
        score=rating.get("score")
        source=rating.get("source")
        if score is not None and source in {"explicit", "explicit_approx"}:
            approximate=source=="explicit_approx"
            prefix="≈" if approximate else ""
            precision="приблизительная" if approximate else "точная"
            lines.append(f"- Оценка: {prefix}{_format_score(score)}/10 ({precision})")

    reaction=signal.get("reaction")
    if isinstance(reaction, Mapping) and reaction.get("source")=="explicit":
        value=reaction.get("value")
        if value in REACTION_LABELS:
            lines.append(f"- Реакция: {REACTION_LABELS[value]}")

    feedback=signal.get("feedback")
    if isinstance(feedback, Mapping):
        summary=_text(feedback.get("summary"))
        if summary:
            lines.append(f"- Отзыв: {summary}")
        explicit=[]
        raw_signals=feedback.get("signals")
        if isinstance(raw_signals, list):
            for item in raw_signals:
                if not isinstance(item, Mapping) or item.get("source")!="explicit":
                    continue
                term=_text(item.get("term"))
                sentiment=SENTIMENT_LABELS.get(item.get("sentiment"))
                strength=item.get("strength")
                if term and sentiment and isinstance(strength, int):
                    explicit.append(f"{term} — {sentiment}, сила {strength}")
        if explicit:
            lines.append("- Явные сигналы:")
            lines.extend(f"  - {item}" for item in sorted(explicit, key=str.casefold))

    return lines


def _target_sections(work: Mapping[str, Any]) -> list[str]:
    sections: list[tuple[str, list[str]]]=[]
    viewers=work.get("viewer_signals") or {}
    groups=work.get("group_signals") or {}

    if isinstance(viewers, Mapping):
        for target, signal in viewers.items():
            if not isinstance(signal, Mapping):
                continue
            lines=_viewer_lines(signal)
            if lines:
                sections.append((str(target), lines))
    if isinstance(groups, Mapping):
        for target, signal in groups.items():
            if not isinstance(signal, Mapping):
                continue
            lines=_viewer_lines(signal)
            if lines:
                sections.append((str(target), lines))

    order={"primary":0,"partner":1,"couple":2}
    sections.sort(key=lambda item:(order.get(item[0],100),item[0].casefold()))
    rendered: list[str]=[]
    for target, lines in sections:
        rendered.extend(["",f"#### {target}",*lines])
    return rendered


def _load_works(media_root: Path) -> list[dict[str, Any]]:
    result=[]
    directory=media_root/"data"/"works"
    if not directory.exists():
        return result
    for path in sorted(directory.glob("*.yaml")):
        data=load_yaml(path) or {}
        if isinstance(data, dict):
            result.append(data)
    result.sort(key=_sort_key)
    return result


def _title_map(works: list[Mapping[str, Any]]) -> dict[str, str]:
    return {
        str(work.get("id")):_work_heading(work)
        for work in works
        if work.get("id")
    }


def _similarity_lines(media_root: Path, titles: Mapping[str, str]) -> list[str]:
    directory=media_root/"data"/"relations"/"similarity"
    result: list[str]=[]
    if not directory.exists():
        return result

    for path in sorted(directory.glob("*.yaml")):
        data=load_yaml(path) or {}
        relations=data.get("relations") or []
        if not isinstance(relations, list):
            continue
        for relation in relations:
            if not isinstance(relation, Mapping):
                continue
            provenance=relation.get("provenance") or {}
            if isinstance(provenance, Mapping) and provenance.get("source")!="explicit":
                continue
            left=relation.get("left") or {}
            right=relation.get("right") or {}
            if not isinstance(left, Mapping) or not isinstance(right, Mapping):
                continue
            if left.get("kind")!="canonical" or right.get("kind")!="canonical":
                continue
            left_title=titles.get(str(left.get("work_id")))
            right_title=titles.get(str(right.get("work_id")))
            if not left_title or not right_title:
                continue
            line=f"- {left_title} ↔ {right_title}"
            note=_text(relation.get("note"))
            if note:
                line += f" — {note}"
            result.append(line)
    return sorted(set(result),key=str.casefold)


def _collection_lines(media_root: Path) -> list[str]:
    directory=media_root/"data"/"collections"
    result=[]
    if not directory.exists():
        return result
    for path in sorted(directory.glob("*.yaml")):
        data=load_yaml(path) or {}
        if not isinstance(data, Mapping):
            continue
        ru=_text(data.get("name_ru"))
        original=_text(data.get("name_original"))
        if ru and original and ru.casefold()!=original.casefold():
            result.append(f"- {ru} / {original}")
        elif ru or original:
            result.append(f"- {ru or original}")
    return sorted(set(result),key=str.casefold)


def render_library_archive(media_root: Path) -> str:
    media_root=Path(media_root)
    works=_load_works(media_root)
    titles=_title_map(works)

    lines=[
        "# Архив медиатеки перед Media Intelligence v6",
        "",
        "> Человекочитаемый снимок старой активной медиатеки перед сбросом v6. "
        "Это памятка и чек-лист, а не машиночитаемый источник восстановления или анализа вкусов.",
        "",
        "## Произведения",
    ]

    for work in works:
        lines.extend(["",f"### {_work_heading(work)}"])
        lines.extend(_target_sections(work))

    similarity=_similarity_lines(media_root,titles)
    lines.extend(["","## Явно заданное сходство"])
    if similarity:
        lines.extend(["",*similarity])
    else:
        lines.extend(["","Явно заданных связей сходства нет."])

    collections=_collection_lines(media_root)
    lines.extend(["","## Подборки"])
    if collections:
        lines.extend(["",*collections])
    else:
        lines.extend(["","Подборок нет."])

    return "\n".join(lines).rstrip()+"\n"


def write_library_archive(repo_root: Path, output: Path) -> Path:
    repo_root=Path(repo_root)
    output=Path(output)
    if not output.is_absolute():
        output=repo_root/output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(render_library_archive(repo_root/"media"),encoding="utf-8")
    return output


def verify_library_archive(repo_root: Path, output: Path) -> list[str]:
    repo_root=Path(repo_root)
    output=Path(output)
    if not output.is_absolute():
        output=repo_root/output
    if not output.exists():
        return [f"Архив не найден: {output}"]
    expected=render_library_archive(repo_root/"media").encode("utf-8")
    actual=output.read_bytes()
    if actual==expected:
        return []
    return ["Архив не совпадает с детерминированной регенерацией из текущих canonical media data."]


def _parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description="Generate or verify the human-readable pre-v6 media archive.")
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--verify",action="store_true")
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args=_parser().parse_args(argv)
    repo_root=args.repo_root.resolve()
    output=args.output
    if args.verify:
        errors=verify_library_archive(repo_root,output)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("Архив точно совпадает с регенерацией из текущих canonical media data.")
        return 0
    written=write_library_archive(repo_root,output)
    print(written)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
