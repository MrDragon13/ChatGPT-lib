from __future__ import annotations

from pathlib import Path

import yaml

from media.tools.archive_library import main as archive_main, render_library_archive, verify_library_archive, write_library_archive


def _dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    root=tmp_path/"repo"
    works=root/"media/data/works"

    _dump(works/"no-signals.yaml",{
        "schema_version":4,
        "id":"internal-no-signals",
        "entity_type":"work",
        "identity":{
            "format":"movie",
            "title_original":"Bare Film",
            "title_ru":"Пустой фильм",
            "year":2001,
            "external_ids":{"tmdb":{"media_type":"movie","id":111}},
        },
        "metadata":{
            "semantic":{
                "traits":[{"term":"story.intrigue","source":"llm_inferred","confidence":"high"}],
                "input_digest":"sha256:"+"1"*64,
                "vocabulary_digest":"sha256:"+"2"*64,
                "algorithm_version":"media-semantic-v1",
            },
        },
        "provenance":{"created_at":"2026-10-01","updated_at":"2026-10-07"},
    })

    _dump(works/"alpha-2010.yaml",{
        "schema_version":4,
        "id":"alpha-2010",
        "entity_type":"work",
        "identity":{
            "format":"movie",
            "title_original":"Alpha",
            "title_ru":"Альфа",
            "year":2010,
            "external_ids":{"tmdb":{"media_type":"movie","id":222},"imdb":"tt0000222"},
        },
        "viewer_signals":{
            "primary":{
                "viewing":{"status":"watched","times_watched":2,"times_watched_approximate":True},
                "rating":{"score":9.0,"source":"explicit","confidence":"exact"},
                "reaction":{"value":"liked","source":"explicit","confidence":"high"},
                "feedback":{
                    "summary":"Очень понравился финал.",
                    "signals":[
                        {"term":"story.intrigue","sentiment":"positive","strength":3,"source":"explicit","confidence":"high"},
                        {"term":"pacing.slow","sentiment":"negative","strength":1,"source":"inferred","confidence":"low"},
                    ],
                },
                "history":[
                    {
                        "at":"2026-10-07T12:00:00Z",
                        "event_id":"123e4567-e89b-42d3-a456-426614174000",
                        "material_evidence":True,
                        "note":"техническая историческая заметка",
                    }
                ],
            },
            "partner":{
                "viewing":{"status":"partial"},
                "rating":{"score":7.5,"source":"explicit_approx","confidence":"medium"},
                "reaction":{"value":"mixed","source":"explicit","confidence":"medium"},
            },
        },
        "group_signals":{
            "couple":{
                "rating":{"score":8.0,"source":"explicit","confidence":"exact"},
                "feedback":{"summary":"Хорошо сработал как совместный просмотр.","signals":[]},
            }
        },
        "provenance":{"created_at":"2026-10-01","updated_at":"2026-10-07"},
    })

    _dump(works/"alpha-2009.yaml",{
        "schema_version":4,
        "id":"alpha-2009",
        "entity_type":"work",
        "identity":{"format":"movie","title_original":"Alpha","title_ru":"Альфа","year":2009},
    })

    _dump(root/"media/data/collections/sample.yaml",{
        "schema_version":4,
        "id":"secret-collection-id",
        "entity_type":"collection",
        "name_ru":"Любимая серия",
        "name_original":"Favourite Series",
        "member_ids":["alpha-2010"],
    })

    _dump(root/"media/data/relations/similarity/primary.yaml",{
        "schema_version":1,
        "target":"primary",
        "relations":[{
            "type":"similar",
            "left":{"kind":"canonical","work_id":"alpha-2010"},
            "right":{"kind":"canonical","work_id":"internal-no-signals"},
            "terms":[],
            "note":"Похожи по ощущению от загадки.",
            "updated_at":"2026-10-07T12:00:00Z",
            "provenance":{"source":"explicit"},
        }],
    })

    _dump(root/"media/preferences/inferred/primary.yaml",{
        "schema_version":1,
        "target":"primary",
        "hypotheses":[{"statement":"SECRET INFERRED HYPOTHESIS"}],
    })
    return root


def test_archive_contains_only_human_useful_pre_reset_data(tmp_path):
    root=_repo(tmp_path)
    text=render_library_archive(root/"media")

    assert "# Архив медиатеки перед Media Intelligence v6" in text
    assert "Альфа / Alpha (2009)" in text
    assert "Альфа / Alpha (2010)" in text
    assert "Пустой фильм / Bare Film (2001)" in text

    assert "#### primary" in text
    assert "Просмотр: просмотрено" in text
    assert "Оценка: 9/10 (точная)" in text
    assert "Реакция: понравилось" in text
    assert "Отзыв: Очень понравился финал." in text
    assert "story.intrigue — положительно, сила 3" in text
    assert "pacing.slow" not in text

    assert "#### partner" in text
    assert "Оценка: ≈7.5/10 (приблизительная)" in text
    assert "Реакция: смешанное впечатление" in text

    assert "#### couple" in text
    assert "Оценка: 8/10 (точная)" in text
    assert "Отзыв: Хорошо сработал как совместный просмотр." in text

    assert "## Явно заданное сходство" in text
    assert "Альфа / Alpha (2010) ↔ Пустой фильм / Bare Film (2001)" in text
    assert "Похожи по ощущению от загадки." in text

    assert "## Подборки" in text
    assert "Любимая серия / Favourite Series" in text

    forbidden=[
        "internal-no-signals",
        "alpha-2010",
        "secret-collection-id",
        "tt0000222",
        "tmdb",
        "123e4567-e89b-42d3-a456-426614174000",
        "sha256:",
        "media-semantic-v1",
        "SECRET INFERRED HYPOTHESIS",
        "техническая историческая заметка",
        "updated_at",
        "provenance",
    ]
    for item in forbidden:
        assert item not in text


def test_work_without_user_data_has_only_heading_before_next_work(tmp_path):
    root=_repo(tmp_path)
    text=render_library_archive(root/"media")
    start=text.index("### Пустой фильм / Bare Film (2001)")
    tail=text[start:]
    boundaries=[position for marker in ("\n### ","\n## ") if (position:=tail.find(marker,1))>=0]
    section=tail[:min(boundaries)] if boundaries else tail
    assert section.strip()=="### Пустой фильм / Bare Film (2001)"


def test_archive_sort_is_deterministic_by_normalized_title_year_then_internal_tiebreaker(tmp_path):
    root=_repo(tmp_path)
    first=render_library_archive(root/"media")
    second=render_library_archive(root/"media")
    assert first==second

    positions=[
        first.index("Альфа / Alpha (2009)"),
        first.index("Альфа / Alpha (2010)"),
        first.index("Пустой фильм / Bare Film (2001)"),
    ]
    assert positions==sorted(positions)


def test_write_and_verify_require_exact_regeneration_not_only_same_entry_count(tmp_path):
    root=_repo(tmp_path)
    output=root/"docs/archive/media-library-before-v6-reset-2026-10-07.md"

    written=write_library_archive(root,output)
    original=written.read_bytes()
    assert verify_library_archive(root,output)==[]

    text=written.read_text(encoding="utf-8")
    written.write_text(text.replace("Очень понравился финал.","Совсем другой отзыв."),encoding="utf-8")
    assert written.read_bytes()!=original

    errors=verify_library_archive(root,output)
    assert errors
    assert any("не совпадает" in error.lower() for error in errors)


def test_verify_reports_missing_archive(tmp_path):
    root=_repo(tmp_path)
    output=root/"docs/archive/missing.md"
    errors=verify_library_archive(root,output)
    assert errors
    assert any("не найден" in error.lower() for error in errors)


def test_archive_cli_write_and_verify(tmp_path, capsys):
    root=_repo(tmp_path)
    relative=Path("docs/archive/review.md")

    assert archive_main(["--repo-root",str(root),"--output",str(relative)])==0
    written=root/relative
    assert written.exists()
    capsys.readouterr()

    assert archive_main(["--repo-root",str(root),"--output",str(relative),"--verify"])==0
    assert "точно совпадает" in capsys.readouterr().out.lower()

    written.write_text(written.read_text(encoding="utf-8")+"\ncorruption\n",encoding="utf-8")
    assert archive_main(["--repo-root",str(root),"--output",str(relative),"--verify"])==1
    assert "не совпадает" in capsys.readouterr().out.lower()
