"""Regression tests for frontend cache-bust discipline."""
from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_PATH = REPO_ROOT / "scripts" / "check_frontend_cache_pins.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_frontend_cache_pins", CHECKER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_concept_page_module_change_requires_app_import_pin_bump() -> None:
    checker = _load_checker()

    failures = checker.validate_changed_cache_pins(
        changed_paths={"public/js/concept-page-view.js"},
        old_files={
            "public/js/app.js": "import './concept-page-view.js?v=14';",
        },
        new_files={
            "public/js/app.js": "import './concept-page-view.js?v=14';",
        },
    )

    assert failures == [
        "public/js/concept-page-view.js changed but public/js/app.js still imports concept-page-view.js?v=14"
    ]


def test_app_bundle_change_requires_index_script_pin_bump() -> None:
    checker = _load_checker()

    failures = checker.validate_changed_cache_pins(
        changed_paths={"public/js/app.js"},
        old_files={
            "public/index.html": '<script type="module" src="js/app.js?v=139"></script>',
        },
        new_files={
            "public/index.html": '<script type="module" src="js/app.js?v=139"></script>',
        },
    )

    assert failures == [
        "public/js/app.js changed but public/index.html still loads app.js?v=139"
    ]


def test_ai_service_change_requires_every_direct_import_pin_bump() -> None:
    checker = _load_checker()

    failures = checker.validate_changed_cache_pins(
        changed_paths={"public/js/ai_service.js"},
        old_files={
            "public/js/app.js": "import './ai_service.js?v=4';",
            "public/js/launch-pad.js": "import './ai_service.js?v=1';",
        },
        new_files={
            "public/js/app.js": "import './ai_service.js?v=4';",
            "public/js/launch-pad.js": "import './ai_service.js?v=1';",
        },
    )

    assert failures == [
        "public/js/ai_service.js changed but public/js/app.js still imports ai_service.js?v=4",
        "public/js/ai_service.js changed but public/js/launch-pad.js still imports ai_service.js?v=1",
    ]


def test_direct_drill_assets_require_index_pin_bumps() -> None:
    checker = _load_checker()

    failures = checker.validate_changed_cache_pins(
        changed_paths={"public/js/drill-chamber.js", "public/css/drill-chamber.css"},
        old_files={
            "public/index.html": """
                <link rel="stylesheet" href="css/drill-chamber.css?v=8">
                <script src="js/drill-chamber.js?v=8"></script>
            """,
        },
        new_files={
            "public/index.html": """
                <link rel="stylesheet" href="css/drill-chamber.css?v=8">
                <script src="js/drill-chamber.js?v=8"></script>
            """,
        },
    )

    assert failures == [
        "public/css/drill-chamber.css changed but public/index.html still loads drill-chamber.css?v=8",
        "public/js/drill-chamber.js changed but public/index.html still loads drill-chamber.js?v=8",
    ]


def test_imported_stylesheet_changes_require_parent_chain_pin_bumps() -> None:
    checker = _load_checker()

    failures = checker.validate_changed_cache_pins(
        changed_paths={
            "public/css/concept-page.css",
            "public/styles.css",
            "public/css/index.css",
        },
        old_files={
            "public/styles.css": "@import './css/concept-page.css?v=35';",
            "public/css/index.css": "@import '../styles.css?v=132' layer(components);",
            "public/index.html": '<link rel="stylesheet" href="/css/index.css?v=134">',
        },
        new_files={
            "public/styles.css": "@import './css/concept-page.css?v=35';",
            "public/css/index.css": "@import '../styles.css?v=132' layer(components);",
            "public/index.html": '<link rel="stylesheet" href="/css/index.css?v=134">',
        },
    )

    assert failures == [
        "public/css/concept-page.css changed but public/styles.css still imports concept-page.css?v=35",
        "public/css/index.css changed but public/index.html still loads index.css?v=134",
        "public/styles.css changed but public/css/index.css still imports styles.css?v=132",
    ]


def test_cache_pin_checker_accepts_bumped_pins() -> None:
    checker = _load_checker()

    failures = checker.validate_changed_cache_pins(
        changed_paths={
            "public/js/concept-page-view.js",
            "public/js/app.js",
            "public/css/concept-page.css",
            "public/styles.css",
            "public/css/index.css",
        },
        old_files={
            "public/js/app.js": "import './concept-page-view.js?v=14';",
            "public/index.html": '<script type="module" src="js/app.js?v=139"></script>',
            "public/styles.css": "@import './css/concept-page.css?v=35';",
            "public/css/index.css": "@import '../styles.css?v=132' layer(components);",
        },
        new_files={
            "public/js/app.js": "import './concept-page-view.js?v=15';",
            "public/index.html": """
                <link rel="stylesheet" href="/css/index.css?v=135">
                <script type="module" src="js/app.js?v=140"></script>
            """,
            "public/styles.css": "@import './css/concept-page.css?v=36';",
            "public/css/index.css": "@import '../styles.css?v=133' layer(components);",
        },
    )

    assert failures == []


def test_coverage_gate_runs_frontend_cache_pin_checker() -> None:
    gate = (REPO_ROOT / "scripts" / "check-coverage.sh").read_text()

    assert "scripts/check_frontend_cache_pins.py" in gate
    assert "RESOLVED_COMPARE_BRANCH" in gate
