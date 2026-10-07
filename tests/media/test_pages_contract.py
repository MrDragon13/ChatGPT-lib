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


def test_pages_build_exposes_only_optional_public_broker_url() -> None:
    text = _workflow_text()
    assert "VITE_MEDIA_BROKER_URL" in text
    assert "vars.MEDIA_BROKER_URL" in text
    assert "secrets.MEDIA_BROKER_URL" not in text
    assert "GITHUB_APP_PRIVATE_KEY" not in text
    assert "GITHUB_APP_CLIENT_SECRET" not in text
    assert "BROKER_SESSION_SECRET" not in text


def test_pages_browser_gate_exercises_production_bundle_without_mock_broker() -> None:
    text = _workflow_text()
    assert "npm run test:e2e -- responsive.spec.ts motion.spec.ts a11y.spec.ts" in text
    assert "edit-feedback.spec.ts" not in text


def test_pages_final_production_build_happens_after_browser_checks() -> None:
    text = _workflow_text()
    browser = text.index("npm run test:e2e -- responsive.spec.ts motion.spec.ts a11y.spec.ts")
    build = text.index("npm run build")
    scan = text.index("npm run scan:dist")
    upload = text.index("actions/upload-pages-artifact@v4")
    assert browser < build < scan < upload, "browser webServer must not overwrite the publishable dist"


def test_media_publish_is_post_merge_and_sha_gated() -> None:
    text=_workflow_text()
    assert "expected_sha:" in text
    assert "publish_mode:" in text
    assert "inputs.expected_sha" in text
    assert "inputs.publish_mode != 'media'" in text
