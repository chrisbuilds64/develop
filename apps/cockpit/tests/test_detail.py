"""The working view: typed blocks, checked before they are drawn; markdown rendered here."""

from cockpit.detail import blocks_for, render_md


class Reader:
    def __init__(self, detail):
        self._d = detail

    def detail(self, access, role, module, config):
        return self._d


def test_a_document_block_arrives_as_html_never_as_raw_markdown():
    blocks = blocks_for(Reader({"blocks": [{"kind": "document", "body": "# Hi\n\n**bold**"}]}), None, None, None, None)
    assert blocks[0]["html"].startswith("<h1>Hi</h1>") and "<strong>bold</strong>" in blocks[0]["html"]
    assert "body" not in blocks[0]


def test_an_unknown_block_kind_is_refused_as_one_hint_block():
    blocks = blocks_for(Reader({"blocks": [{"kind": "chart"}]}), None, None, None, None)
    assert len(blocks) == 1 and "does not match the contract" in blocks[0]["html"]


def test_a_reader_without_detail_gives_no_blocks():
    assert blocks_for(object(), None, None, None, None) == []


def test_a_crashing_reader_is_a_block_not_an_exception():
    class Bad:
        def detail(self, *a):
            raise RuntimeError("boom")
    blocks = blocks_for(Bad(), None, None, None, None)
    assert "RuntimeError: boom" in blocks[0]["html"]


def test_markdown_tables_render():
    assert "<table>" in render_md("| a | b |\n|---|---|\n| 1 | 2 |")
