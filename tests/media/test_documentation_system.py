from __future__ import annotations

import re
from pathlib import Path


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
