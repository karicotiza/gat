"""FastAPI Tests."""

from fastapi.testclient import TestClient

from src.main import Settings, app
from tests.utils_for_tests import check

test_client: TestClient = TestClient(app)
done_true: str = r'{"text":"Done","done":true}\n'


def test_very_long_text() -> None:
    """Test very long text."""
    very_long_text: str = 'a' * (Settings.request_max_length - 1)
    check(test_client, very_long_text)


def test_sentence_with_terminal() -> None:
    """Test text with terminal punctuation marks."""
    text_with_terminal: str = 'aaa... a, aa'
    text_with_terminal_expected: str = ''.join((
        r'{"text":"aaa...","done":false}\n',
        r'{"text":"a,","done":false}\n',
        r'{"text":"aa","done":false}\n',
        done_true,
    ))

    check(
        test_client,
        text_with_terminal,
        text_with_terminal_expected,
    )


def test_sentence_with_internal() -> None:
    """Test text with internal punctuation marks."""
    text_with_internal: str = 'aaa, a, aa'
    text_with_internal_expected: str = ''.join((
        r'{"text":"aaa, a,","done":false}\n',
        r'{"text":"aa","done":false}\n',
        done_true,
    ))

    check(
        test_client,
        text_with_internal,
        text_with_internal_expected,
    )


def test_sentence_with_spaces() -> None:
    """Test text with spaces only."""
    text_with_spaces: str = 'aaa a aa'
    text_with_spaces_expected: str = ''.join((
        r'{"text":"aaa a","done":false}\n',
        r'{"text":"aa","done":false}\n',
        done_true,
    ))

    check(
        test_client,
        text_with_spaces,
        text_with_spaces_expected,
    )


def test_sentence_without_spaces() -> None:
    """Test text without spaces and any punctuation marks."""
    text_without_spaces: str = 'aaaaa'
    text_without_spaces_expected: str = ''.join((
        r'{"text":"aaaaa","done":false}\n',
        done_true,
    ))

    check(
        test_client,
        text_without_spaces,
        text_without_spaces_expected,
    )
