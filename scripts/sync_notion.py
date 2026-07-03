import argparse
import os
from pathlib import Path
from typing import Any

import httpx


def build_payload(parent_page_id: str, markdown: str) -> dict[str, Any]:
    return {
        "parent": {"page_id": parent_page_id},
        "markdown": markdown,
        "allow_async": False,
    }


def sync_markdown(path: Path) -> str:
    token = os.environ.get("NOTION_TOKEN")
    parent_page_id = os.environ.get("NOTION_PARENT_PAGE_ID")
    notion_version = os.environ.get("NOTION_VERSION", "2026-03-11")
    if not token or not parent_page_id:
        raise SystemExit(
            "NOTION_TOKEN and NOTION_PARENT_PAGE_ID are required. "
            "Store them as GitHub Actions secrets."
        )
    markdown = path.read_text(encoding="utf-8")
    response = httpx.post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": notion_version,
            "Content-Type": "application/json",
        },
        json=build_payload(parent_page_id, markdown),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return str(data.get("url", data.get("id", "created")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish repository Markdown to Notion")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(sync_markdown(args.path))


if __name__ == "__main__":
    main()
