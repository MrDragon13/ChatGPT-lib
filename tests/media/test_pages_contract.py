from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "media-pages.yml"


def _workflow_text() -> str:
    assert WORKFLOW.exists(), "media-pages.yml must exist"
    return WORKFLOW.read_text(encoding="utf-8")


def test_pages_workflow_runs_full_read_only_gate_before_build() -> None:
    text = _workflow_text()
    required = [
        "python -m media.tools.validate .",
        "python -m media.cli rebuild --check",
        "python -m media.cli doctor --format json",
        "python -m media.cli web-export --output web/public/data/manifest.json --format json",
        "npm ci",
        "npm run test:run",
        "npm run typecheck",
        "npm run build",
    ]
    positions = [text.index(fragment) for fragment in required]
    assert positions == sorted(positions), "validation/export/frontend gate order changed"


def test_pages_workflow_uses_pages_artifact_and_deploy_only_for_main() -> None:
    text = _workflow_text()
    assert "actions/configure-pages@v5" in text
    assert "actions/upload-pages-artifact@v4" in text
    assert "actions/deploy-pages@v4" in text
    assert "path: web/dist" in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "pages: write" in text
    assert "id-token: write" in text


def test_pages_workflow_does_not_reference_provider_or_write_credentials() -> None:
    text = _workflow_text().lower()
    forbidden = [
        "tmdb" + "_read_token",
        "client" + "_secret",
        "private" + "_key",
        "media" + "_write_token",
    ]
    assert all(value not in text for value in forbidden)
