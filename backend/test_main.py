from __future__ import annotations

from types import SimpleNamespace

from main import ChatMessage, _to_api_messages


def _human(content):
    return SimpleNamespace(type="human", content=content)


def _ai(content):
    return SimpleNamespace(type="ai", content=content)


def test_to_api_messages_skips_empty_ai_messages():
    """AI messages with no displayable text should be skipped."""
    lc_messages = [
        _human("Hello"),
        _ai(""),  # empty assistant content (e.g. tool-only message)
        _ai("Final answer"),
    ]

    api_messages = _to_api_messages(lc_messages)

    # Expect one user + one assistant with non-empty content
    assert [m.role for m in api_messages] == ["user", "assistant"]
    assert api_messages[0].content == "Hello"
    assert api_messages[1].content == "Final answer"


def test_to_api_messages_handles_list_content_and_filters_empty():
    """List-based AI content should be flattened and empty lists skipped."""
    # Simulate a tool-call-only message followed by a text chunk
    tool_only = [
        {"type": "tool_use", "id": "1", "name": "search_professors"},
    ]
    text_chunk = [
        {"type": "text", "text": "Visible answer"},
    ]

    lc_messages = [
        _human("Question"),
        _ai(tool_only),
        _ai(text_chunk),
    ]

    api_messages = _to_api_messages(lc_messages)

    assert [m.role for m in api_messages] == ["user", "assistant"]
    assert api_messages[0].content == "Question"
    assert api_messages[1].content == "Visible answer"

