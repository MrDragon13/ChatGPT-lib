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


def test_starter_prompt_is_human_first_and_reuses_repository_rules():
    text = _text("media/START_PROMPT.md")
    assert "личный киноассистент" in text
    assert "Всю техническую работу" in text
    assert "не превращай выбор фильма в анкету" in text
    assert "один короткий необязательный вопрос" in text
    assert "ничего в медиатеке не записывай" in text
