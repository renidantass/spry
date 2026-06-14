"""Build script: generates static documentation site for CDN deployment."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from spry.testing import TestClient

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dist"
BASE_URL = os.environ.get("SPRY_DOCS_BASE_URL", "")

DOC_PAGES = [
    "getting-started",
    "api-development",
    "mvc-development",
    "orm-data",
    "auth-security",
    "tooling-cli",
    "testing",
    "deployment",
    "architecture",
    "troubleshooting",
]

API_PAGES = [
    "app", "http", "orm", "routing", "di", "auth",
    "validation", "views", "testing", "session",
    "events", "tasks", "cors", "i18n",
]

LOCALES = ["pt", "en"]


def _write_page(client: TestClient, url_path: str, output_path: Path) -> None:
    resp = client.get(url_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(resp.text, encoding="utf-8")
    print(f"  [OK] {url_path}")


def build() -> None:
    from spry_docs.app import create_app

    app = create_app()
    client = TestClient(app)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    assets_src = Path(__file__).resolve().parent.parent / "src" / "spry_docs" / "assets"
    assets_dst = OUTPUT_DIR / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst)

    # Landing page (default locale)
    _write_page(client, BASE_URL or "/", OUTPUT_DIR / "index.html")

    # Documentation pages for each locale
    for loc in LOCALES:
        for slug in DOC_PAGES:
            _write_page(
                client,
                f"{BASE_URL}/{loc}/docs/{slug}",
                OUTPUT_DIR / loc / "docs" / slug / "index.html",
            )

    # API pages (locale-independent)
    _write_page(client, f"{BASE_URL}/api/", OUTPUT_DIR / "api" / "index.html")
    _write_page(client, f"{BASE_URL}/api", OUTPUT_DIR / "api" / "index.html")
    for mod in API_PAGES:
        _write_page(
            client,
            f"{BASE_URL}/api/{mod}",
            OUTPUT_DIR / "api" / mod / "index.html",
        )

    # Changelog (default locale)
    _write_page(client, f"{BASE_URL}/changelog", OUTPUT_DIR / "changelog" / "index.html")

    # Playground (default locale)
    _write_page(client, f"{BASE_URL}/playground", OUTPUT_DIR / "playground" / "index.html")

    # Search index per locale
    for loc in LOCALES:
        _write_page(
            client,
            f"{BASE_URL}/search-index.json?locale={loc}",
            OUTPUT_DIR / loc / "search-index.json",
        )

    print(f"\nBuild complete: {OUTPUT_DIR}")


if __name__ == "__main__":
    build()
