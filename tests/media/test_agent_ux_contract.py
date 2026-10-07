from pathlib import Path


ROOT = Path(__file__).parents[2]
SCENARIO_CATALOG = "docs/superpowers/specs/2026-10-07-media-v6-agent-scenario-catalog.md"


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_agent_contract_keeps_technical_details_hidden_by_default():
    text=_text("media/AGENTS.md")
    assert "## Пользовательский договор" in text
    assert "Не пересказывай пользователю обычную механику GitHub" in text
    assert "Технические детали — информация для исключений" in text
    assert "Один короткий необязательный вопрос" in text
    assert "не должен блокировать" in text


def test_feedback_write_does_not_require_second_confirmation_and_pending_is_not_saved():
    text=_text("media/AGENTS.md")
    assert "это уже разрешение довести обычную запись до конца" in text
    assert "Не проси второго подтверждения" in text
    assert "Никогда не говори «сохранено», пока результат не присутствует в актуальном `main`" in text
    assert "разговор можно продолжать сразу" in text


def test_normal_data_write_has_one_guarded_v6_merge_path():
    command=_text(".github/workflows/media-command.yml")
    assert "v6_single_runner" in command
    assert "Merge checked v6 operation" in command
    assert "media-pages.yml" in command
    assert "media-check.yml" not in command
    assert "media-auto-merge.yml" not in command
    assert "Leave manual operation ready for review" in command
    assert not (ROOT/".github/workflows/media-check.yml").exists()
    assert not (ROOT/".github/workflows/media-auto-merge.yml").exists()


def test_starter_prompt_is_human_first_and_reuses_repository_rules():
    text=_text("media/START_PROMPT.md")
    for phrase in (
        "личный киноассистент",
        "Всю техническую работу доводи сам",
        "Не превращай выбор фильма в анкету",
        "один короткий необязательный вопрос",
        "ничего в медиатеке не записывай",
        "не проси второго подтверждения",
        "не говори, что данные сохранены",
    ):
        assert phrase in text
    assert "media/AGENTS.md" in text
    assert len(text)<5500


def test_v6_agent_contract_has_complete_intent_router():
    text=_text("media/AGENTS.md")
    assert "Media Intelligence v6" in text
    assert "## Маршрутизация намерений" in text
    for route in (
        "read / lookup",
        "record",
        "correct / clear / purge",
        "interest",
        "recommend internal",
        "recommend external",
        "assess candidate",
        "similarity write / similarity remove",
        "reanalyze taste",
        "semantic enrich",
        "metadata maintenance",
        "architecture / vocabulary maintenance",
    ):
        assert route in text


def test_v6_recommendation_routes_distinguish_internal_and_external_discovery():
    text=_text("media/AGENTS.md")
    assert "Общий запрос на рекомендацию по умолчанию допускает внешний поиск" in text
    assert "Рекомендацию только из медиатеки" in text
    assert "локальной библиотекой" in text
    assert "record_recommendation_interaction" in text


def test_v6_agent_routes_reanalysis_and_semantics_safely():
    text=_text("media/AGENTS.md")
    assert "set_inferred_preferences" in text
    assert "set_semantic_fingerprint" in text
    assert "Выведенный результат не является независимым доказательством" in text
    assert "Семантический отпечаток описывает произведение, а не реакцию зрителя" in text
    assert "Порог по умолчанию — **5**" in text


def test_v6_agent_routes_candidate_assessment_and_similarity_safely():
    text=_text("media/AGENTS.md")
    for phrase in (
        "assess candidate",
        "similarity write / similarity remove",
        "assess_candidate",
        "set_work_similarity",
        "remove_work_similarity",
        "не является устойчивым предпочтением",
        "не создаёт произведение в медиатеке",
        "Не выдавай qualitative assessment за точную вероятность",
    ):
        assert phrase in text


def test_v6_agent_requires_honest_limitations_and_basis_language():
    text=_text("media/AGENTS.md")
    for phrase in (
        "`ranking_basis=none` не является персональным семантическим основанием",
        "Неполное `assessment_coverage` нельзя описывать как полностью обоснованную уверенность",
        "Активные `limitations` важны для вывода",
        "не повторяй одно и то же предупреждение механически",
    ):
        assert phrase in text


def test_same_work_pending_contract_keeps_second_clarification_local():
    text=_text("media/AGENTS.md")
    assert "не создавай второй параллельный request PR" in text
    assert "перечитай свежий `media_entry_context`" in text
    assert "viewer digest" in text
    catalog=_text(SCENARIO_CATALOG)
    assert "второй request PR по тому же work/target не создаётся" in catalog
    assert "локальном слое текущей LLM-сессии" in catalog
    assert "получает свежий viewer digest" in catalog


def test_v6_scenario_catalog_covers_required_end_to_end_cases():
    text=_text(SCENARIO_CATALOG)
    for phrase in (
        "Отзыв о существующем произведении",
        "Новое произведение",
        "Порог повторного анализа 4 → 5",
        "Рекомендация для пары",
        "Неясная identity или недоступный provider",
        "Повтор операции",
        "Старый фильм из pre-v6 архива",
        "Web feedback",
        "set_work_similarity",
        "remove_work_similarity",
        "assess_candidate",
    ):
        assert phrase in text


def test_repository_root_has_compact_agent_router_to_living_docs():
    text=_text("AGENTS.md")
    for phrase in ("media/AGENTS.md","docs/README.md","docs/status/current.md","media/START_PROMPT.md"):
        assert phrase in text
    assert "source of truth" in text.lower()
    assert "historical" in text.lower()
    assert len(text)<4000


def test_starter_prompt_bootstrap_has_no_legacy_pilot_dependency():
    text=_text("media/START_PROMPT.md")
    assert "media/AGENTS.md" in text
    assert "legacy reassessment" not in text.lower()
    assert "media/V5_STATUS.md" not in text
    assert "Старая медиатека до v6" in text
    assert len(text)<5500


def test_media_agent_contract_declares_living_docs_and_current_scenario_catalog():
    text=_text("media/AGENTS.md")
    assert "docs/architecture/" in text
    assert "docs/reference/" in text
    assert SCENARIO_CATALOG in text
    assert "Исторические спецификации" in text
    assert "не заменяют текущий код и живую документацию" in text


def test_root_readme_points_to_v6_and_current_web_write_path():
    text=_text("README.md")
    assert "Media Intelligence v6" in text
    assert "media/README.md" in text
    assert "record_media_entry" in text
    assert "Broker" in text
