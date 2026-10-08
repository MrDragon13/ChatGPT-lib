from __future__ import annotations

import re
from pathlib import Path

from media.commands.schema import _SCHEMA_BY_OPERATION
from media.service.web_export import WEB_MANIFEST_SCHEMA_VERSION


ROOT = Path(__file__).parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _local_markdown_targets(path: str | Path) -> list[Path]:
    source = ROOT / Path(path)
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    targets: list[Path] = []
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        clean = target.split("#", 1)[0]
        if not clean:
            continue
        targets.append((source.parent / clean).resolve())
    return targets


def test_root_readme_routes_to_documentation_usage_development_and_architecture():
    text = _text("README.md")
    for target in ("docs/README.md", "docs/guides/media-usage.md", "docs/guides/development.md", "docs/architecture/overview.md"):
        assert f"]({target})" in text


def test_docs_index_separates_living_agent_and_historical_layers():
    text = _text("docs/README.md")
    assert "living" in text.lower() or "живая" in text.lower()
    assert "AGENTS.md" in text
    assert "media/AGENTS.md" in text
    assert "operating contract" in text.lower() or "операцион" in text.lower() or "рабочий договор" in text.lower()
    assert "docs/superpowers/" in text
    assert "historical" in text.lower() or "истор" in text.lower()


def test_root_readme_does_not_publish_dated_specs_as_current_architecture():
    text = _text("README.md")
    assert "## Актуальная архитектура v5" not in text
    assert not re.search(r"(?is)(current|актуальн)[^\n]{0,80}docs/superpowers/(?:specs|plans)/20\d\d-", text)


def test_architecture_layer_covers_current_v6_without_historical_specs():
    overview = _text("docs/architecture/overview.md")
    media_model = _text("docs/architecture/media-model.md")
    overview_lower = overview.lower()
    concepts = (
        ("canonical", "канонич"),
        ("derived", "производн"),
        ("github actions", "github"),
        ("broker", "broker"),
        ("web manifest", "web manifest"),
    )
    for english, russian in concepts:
        assert english in overview_lower or russian in overview_lower
    for phrase in ("primary", "partner", "couple", "semantic fingerprint", "similarity", "WorkRef", "reconciliation"):
        assert phrase.lower() in media_model.lower()
    assert not re.search(r"docs/superpowers/(?:specs|plans)/20\d\d-", overview)


def test_intelligence_doc_keeps_similarity_as_evidence_not_preference():
    text = _text("docs/architecture/intelligence.md").lower()
    assert "similarity" in text
    assert "evidence" in text or "свидетель" in text
    assert "не является preference" in text or "не становится preference" in text
    assert "independent" in text or "независим" in text


def test_candidate_assessment_doc_is_read_only_and_qualitative():
    text = _text("docs/architecture/intelligence.md").lower()
    assert "assess_candidate" in text
    assert "read-only" in text
    assert "qualitative" in text or "качествен" in text
    assert "fake precise" in text or "точн" in text
    assert "opaque match score" in text or "match score" in text


def test_web_architecture_manifest_version_matches_exporter():
    text = _text("docs/architecture/web-and-broker.md")
    match = re.search(r"Current manifest version:\s*v(\d+)", text)
    assert match is not None
    assert int(match.group(1)) == WEB_MANIFEST_SCHEMA_VERSION


def test_write_pipeline_separates_normal_typed_and_manual_developer_routes():
    text = _text("docs/architecture/write-pipeline.md").lower()
    for phrase in ("request-only", "operation pr", "deterministic transaction", "exact checked head", "github api", "pages"):
        assert phrase in text
    assert "developer changes" in text
    assert "refresh_metadata" in text
    assert "manual_review" in text


def test_media_command_reference_matches_registered_operations():
    text = _text("docs/reference/media-commands.md")
    documented = set(re.findall(r"^\| `([a-z0-9_]+)` \|", text, flags=re.MULTILINE))
    assert documented == set(_SCHEMA_BY_OPERATION)


def test_operations_guide_uses_existing_verification_commands():
    text = _text("docs/guides/operations.md")
    for command in (
        "python -m pytest -q", "python -m media.tools.validate .", "python -m media.cli rebuild --check",
        "python -m media.cli doctor --format json", "python -m media.cli web-export", "npm run test:run",
        "npm run typecheck", "npm run build",
    ):
        assert command in text


def test_reference_invariants_include_cross_system_safety_rules():
    text = _text("docs/reference/invariants.md").lower()
    concepts = (
        ("canonical", "канонич"),
        ("generated", "generated"),
        ("typed command", "типизирован"),
        ("similarity", "similarity"),
        ("preference", "preference"),
        ("target", "target"),
        ("browser", "браузер"),
        ("secret", "секрет"),
        ("unknown", "неизвест"),
        ("vocabulary", "словар"),
    )
    for english, russian in concepts:
        assert english in text or russian in text


def test_current_status_is_durable_not_a_pr_ledger():
    text = _text("docs/status/current.md")
    for required in ("Media Intelligence v6", "record_media_entry", "assess_candidate", "set_work_similarity", "manifest", "v4", "empty_library"):
        assert required in text
    for forbidden in ("Current head:", "Media Dev Check #", "Web Check #", "Task 1", "Task 2", "resume from branch"):
        assert forbidden not in text


def test_media_usage_covers_similarity_and_candidate_assessment():
    text = _text("docs/guides/media-usage.md").lower()
    for phrase in ("assess_candidate", "set_work_similarity", "remove_work_similarity", "primary", "partner", "couple"):
        assert phrase in text
    assert "external" in text or "внешн" in text
    assert "не добав" in text and "медиатек" in text


def test_media_readme_is_compact_subsystem_router():
    text = _text("media/README.md")
    for target in ("../docs/architecture/media-model.md", "../docs/architecture/intelligence.md", "../docs/guides/media-usage.md", "../docs/reference/media-commands.md", "../docs/status/current.md"):
        assert f"]({target})" in text
    assert len(text) < 7000




def test_product_and_design_are_explicitly_scoped_to_media_web():
    product = _text("PRODUCT.md")
    design = _text("DESIGN.md")
    assert "media-web" in product.lower()
    assert "архитектур" in product.lower()
    assert "product: media-web" in design
    assert "# Дизайн-система Media Web" in design


def test_agent_bootstrap_does_not_require_historical_specs_or_long_status():
    root = _text("AGENTS.md")
    media = _text("media/AGENTS.md")
    assert "docs/README.md" in root
    assert "docs/status/current.md" in root
    assert "Read `media/V5_STATUS.md` second" not in root
    assert "docs/architecture/" in media
    assert "docs/reference/" in media
    assert "media/V5_STATUS.md" not in media


def test_key_living_documentation_local_links_resolve():
    paths = [
        Path("README.md"), Path("AGENTS.md"), Path("media/README.md"), Path("media/AGENTS.md"),
        Path("media/START_PROMPT.md"), Path("docs/README.md"),
    ]
    for directory in ("docs/architecture", "docs/guides", "docs/reference", "docs/status"):
        paths.extend(path.relative_to(ROOT) for path in sorted((ROOT / directory).glob("*.md")))

    for path in paths:
        source = ROOT / path
        assert source.exists(), str(path)
        for target in _local_markdown_targets(path):
            display = target.relative_to(ROOT) if target.is_relative_to(ROOT) else target
            assert target.exists(), f"broken local Markdown link: {path} -> {display}"
