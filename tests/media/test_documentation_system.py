from __future__ import annotations

import re
from pathlib import Path

from media.service.web_export import WEB_MANIFEST_SCHEMA_VERSION


ROOT = Path(__file__).parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _local_markdown_targets(path: str) -> list[Path]:
    source = ROOT / path
    text = source.read_text(encoding="utf-8")
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
    for target in (
        "docs/README.md",
        "docs/guides/media-usage.md",
        "docs/guides/development.md",
        "docs/architecture/overview.md",
    ):
        assert f"]({target})" in text


def test_docs_index_separates_living_agent_and_historical_layers():
    text = _text("docs/README.md")
    assert "living" in text.lower()
    assert "AGENTS.md" in text
    assert "media/AGENTS.md" in text
    assert "operating contract" in text.lower() or "операцион" in text.lower()
    assert "docs/superpowers/" in text
    assert "historical" in text.lower() or "истор" in text.lower()


def test_root_readme_does_not_publish_dated_specs_as_current_architecture():
    text = _text("README.md")
    assert "## Актуальная архитектура v5" not in text
    assert not re.search(
        r"(?is)(current|актуальн)[^\n]{0,80}docs/superpowers/(?:specs|plans)/20\d\d-",
        text,
    )


def test_architecture_layer_covers_current_v51_without_historical_specs():
    overview = _text("docs/architecture/overview.md")
    media_model = _text("docs/architecture/media-model.md")
    for phrase in (
        "canonical",
        "derived",
        "GitHub Actions",
        "broker",
        "web manifest",
    ):
        assert phrase.lower() in overview.lower()
    for phrase in (
        "primary",
        "partner",
        "couple",
        "semantic fingerprint",
        "similarity",
        "WorkRef",
        "reconciliation",
    ):
        assert phrase.lower() in media_model.lower()
    assert not re.search(r"docs/superpowers/(?:specs|plans)/20\d\d-", overview)


def test_intelligence_doc_keeps_similarity_as_evidence_not_preference():
    text = _text("docs/architecture/intelligence.md").lower()
    assert "similarity" in text
    assert "evidence" in text or "свидетель" in text
    assert "не является preference" in text or "не становится preference" in text
    assert "independent" in text


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
    for phrase in (
        "typed request",
        "operation pr",
        "deterministic transaction",
        "exact-head",
        "guarded merge",
        "pages",
    ):
        assert phrase in text
    assert "manual developer" in text
    assert "refresh_metadata" in text
