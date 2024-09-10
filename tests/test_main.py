"""FastAPI Tests."""

from fastapi.testclient import TestClient
from utils_for_tests import check

from src.main import Settings, app

test_client: TestClient = TestClient(app)


def test_very_long_text() -> None:
    """Test very long text."""
    very_long_text: str = 'a' * (Settings.request_max_length - 1)
    check(test_client, very_long_text)


def test_sentence_with_terminal() -> None:
    """Test text with terminal punctuation marks."""
    text_with_terminal: str = 'aaa... a, aa'
    check(
        test_client,
        text_with_terminal,
        r'{"text":"aaa...","done":false}\n{"text":"Done","done":true}\n',
    )


def test_sentence_with_internal() -> None:
    """Test text with internal punctuation marks."""
    text_with_internal: str = 'aaa, a, aa'
    check(
        test_client,
        text_with_internal,
        r'{"text":"aaa, a,","done":false}\n{"text":"Done","done":true}\n',
    )


def test_sentence_with_spaces() -> None:
    """Test text with spaces only."""
    text_with_spaces: str = 'aaa a aa'
    check(
        test_client,
        text_with_spaces,
        r'{"text":"aaa a","done":false}\n{"text":"Done","done":true}\n',
    )


def test_sentence_without_spaces() -> None:
    """Test text without spaces and any punctuation marks."""
    text_without_spaces: str = 'aaaaa'
    check(
        test_client,
        text_without_spaces,
        r'{"text":"aaaaa","done":false}\n{"text":"Done","done":true}\n',
    )
