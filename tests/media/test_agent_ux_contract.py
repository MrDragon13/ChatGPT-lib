from pathlib import Path


ROOT = Path(__file__).parents[2]


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
    assert "workflows: [Media Check]" in text
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "github.event.workflow_run.event == 'workflow_dispatch'" in text
    assert "startsWith(github.event.workflow_run.head_branch, 'media/op-')" in text
    assert "head.sha" in text
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
