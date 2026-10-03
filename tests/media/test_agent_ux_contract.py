from pathlib import Path


ROOT = Path(__file__).parents[2]
SCENARIO_CATALOG = "docs/superpowers/specs/2026-10-03-media-v5-agent-scenario-catalog.md"


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_agent_contract_keeps_technical_details_hidden_by_default():
    text = _text("media/AGENTS.md")
    assert "## User experience contract" in text
    assert "Do not narrate routine GitHub" in text
    assert "Technical details are exception-path information" in text
    assert "one short optional follow-up question" in text
    assert "must not block recording" in text


def test_feedback_write_does_not_require_second_confirmation():
    text = _text("media/AGENTS.md")
    assert "A clear request to record or save media feedback is authorization to complete the normal data write" in text
    assert "Do not ask for a second confirmation just to merge or finalize that same normal data operation" in text
    assert "Never say that data was saved until it is actually present on `main`" in text


def test_normal_data_write_has_guarded_auto_merge_workflow():
    text = _text(".github/workflows/media-auto-merge.yml")
    assert "workflow_run:" in text
    assert "workflows: [Media Command]" in text
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "github.event.workflow_run.event == 'pull_request'" in text
    assert "startsWith(github.event.workflow_run.head_branch, 'media/op-')" in text
    assert "media-check.yml" in text
    assert "event=workflow_dispatch" in text
    assert "head_sha" in text
    assert "base.ref" in text
    assert "media/data/works/" in text
    assert ".media/operations/" in text
    assert "merge" in text


def test_starter_prompt_is_human_first_and_reuses_repository_rules():
    text = _text("media/START_PROMPT.md")
    assert "личный киноассистент" in text
    assert "Всю техническую работу" in text
    assert "не превращай выбор фильма в анкету" in text
    assert "один короткий необязательный вопрос" in text
    assert "ничего в медиатеке не записывай" in text
    assert "не проси второго подтверждения" in text
    assert "не говори, что сохранил" in text


def test_v5_agent_contract_has_complete_intent_router():
    text = _text("media/AGENTS.md")
    assert "Media Intelligence v5" in text
    assert "## Intent router" in text
    for route in (
        "read / lookup",
        "record",
        "correct",
        "clear",
        "purge",
        "interest",
        "recommend internal",
        "recommend external",
        "explain",
        "reanalyze taste",
        "semantic enrich",
        "metadata maintenance",
        "architecture/vocabulary maintenance",
    ):
        assert route in text


def test_v5_recommendation_routes_distinguish_internal_from_external_discovery():
    text = _text("media/AGENTS.md")
    assert "External discovery is the default for a general recommendation request" in text
    assert "Internal-only recommendation" in text
    assert "local media is memory, exclusion, and evidence, not the candidate boundary" in text
    assert "not_tonight" in text
    assert "record_recommendation_interaction" in text


def test_v5_agent_contract_routes_reanalysis_and_semantic_enrichment_safely():
    text = _text("media/AGENTS.md")
    assert "taste-context" in text
    assert "set_inferred_preferences" in text
    assert "set_semantic_fingerprint" in text
    assert "Inferred output is not independent evidence for another inferred output" in text
    assert "Film fingerprint describes the work, never the viewer reaction" in text


def test_v5_starter_prompt_mentions_new_user_capabilities_without_becoming_manual():
    text = _text("media/START_PROMPT.md")
    assert "исправлять и удалять" in text
    assert "переанализировать мой вкус" in text
    assert "из моей медиатеки" in text
    assert "внешний поиск" in text
    assert "media/AGENTS.md" in text
    assert len(text) < 8000


def test_repository_root_has_compact_agent_router():
    text = _text("AGENTS.md")
    assert "media/AGENTS.md" in text
    assert "media/V5_STATUS.md" in text
    assert "media/START_PROMPT.md" in text
    assert "source of truth" in text.lower()
    assert len(text) < 4000


def test_starter_prompt_has_deterministic_bootstrap_and_no_stale_privacy_claim():
    text = _text("media/START_PROMPT.md")
    agents_pos = text.index("media/AGENTS.md")
    status_pos = text.index("media/V5_STATUS.md")
    assert agents_pos < status_pos
    assert "связанные с ними файлы" not in text
    assert "приватный GitHub-репозиторий" not in text
    assert len(text) < 5500


def test_media_agent_contract_declares_read_order_and_conditional_scenario_catalog():
    text = _text("media/AGENTS.md")
    assert "## Operating model" in text
    assert "media/V5_STATUS.md" in text
    assert SCENARIO_CATALOG in text
    assert "only when" in text.lower()


def test_root_readme_points_to_v5_and_current_web_write_path():
    text = _text("README.md")
    assert "[Personal Media Library v5](media/README.md)" in text
    assert "будущие быстрые правки" not in text
    assert "typed-command broker" in text
