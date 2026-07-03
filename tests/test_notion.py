from scripts.sync_notion import build_payload


def test_build_notion_markdown_payload():
    payload = build_payload("page-id", "# 調査報告")
    assert payload == {
        "parent": {"page_id": "page-id"},
        "markdown": "# 調査報告",
        "allow_async": False,
    }
