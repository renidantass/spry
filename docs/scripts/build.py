"""Build script: generates static documentation site for CDN deployment."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from spry.testing import TestClient

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dist"
BASE_URL = os.environ.get("SPRY_DOCS_BASE_URL", "")

PAGES = [
    "/",
    "/docs/getting-started",
    "/docs/api-development",
    "/docs/mvc-development",
    "/docs/orm-data",
    "/docs/auth-security",
    "/docs/tooling-cli",
    "/docs/testing",
    "/docs/deployment",
    "/docs/architecture",
    "/docs/troubleshooting",
    "/changelog",
    "/playground",
    "/api/",
    "/api/app",
    "/api/http",
    "/api/orm",
    "/api/routing",
    "/api/di",
    "/api/auth",
    "/api/validation",
    "/api/views",
    "/api/testing",
    "/api/session",
    "/api/events",
    "/api/tasks",
    "/api/cors",
    "/api/i18n",
]


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

    for page in PAGES:
        page_path = BASE_URL if page == "/" else f"{BASE_URL}{page.rstrip('/')}"
        resp = client.get(page_path)
        file_path = OUTPUT_DIR / page.lstrip("/") / "index.html"
        if page == "/":
            file_path = OUTPUT_DIR / "index.html"
        elif not page.endswith("/"):
            file_path = OUTPUT_DIR / page.lstrip("/") / "index.html"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(resp.text, encoding="utf-8")
        print(f"  [OK] {page}")

    resp = client.get(f"{BASE_URL}/search-index.json")
    (OUTPUT_DIR / "search-index.json").write_text(resp.text, encoding="utf-8")

    print(f"\nBuild complete: {OUTPUT_DIR}")


if __name__ == "__main__":
    build()
