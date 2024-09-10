"""Tests."""

from fastapi.testclient import TestClient
from httpx import Response
from schemathesis import experimental, models
from schemathesis.specs.openapi import loaders, schemas

from src.main import Settings, app

experimental.OPEN_API_3_1.enable()

test_client: TestClient = TestClient(app)
schema: schemas.BaseOpenAPISchema = loaders.from_asgi('/openapi.json', app)


@schema.parametrize()
async def test_schemathesis(case: models.Case) -> None:
    """Schemathesis tests.

    Args:
        case (models.Case): Schemathesis injection.
    """
    case.call_and_validate()


def _check(before: str, after: str | None = None) -> None:
    success_code: int = 200
    response: Response = test_client.post('/', json={'text': before})

    if response.status_code != success_code:
        raise ValueError('Failed')

    if after and str(response.content)[2:-1] != after:
        raise ValueError()


def test_very_long_text() -> None:
    """Test very long text."""
    very_long_text: str = 'a' * (Settings.request_max_length - 1)
    _check(very_long_text)


def test_sentence_with_terminal() -> None:
    """Test text with terminal punctuation marks."""
    text_with_terminal: str = 'aaa... a, aa'
    _check(
        text_with_terminal,
        r'{"text":"aaa...","done":false}\n{"text":"Done","done":true}\n',
    )


def test_sentence_with_internal() -> None:
    """Test text with internal punctuation marks."""
    text_with_internal: str = 'aaa, a, aa'
    _check(
        text_with_internal,
        r'{"text":"aaa, a,","done":false}\n{"text":"Done","done":true}\n',
    )


def test_sentence_with_spaces() -> None:
    """Test text with spaces only."""
    text_with_spaces: str = 'aaa a aa'
    _check(
        text_with_spaces,
        r'{"text":"aaa a","done":false}\n{"text":"Done","done":true}\n',
    )


def test_sentence_without_spaces() -> None:
    """Test text without spaces and any punctuation marks."""
    text_without_spaces: str = 'aaaaa'
    _check(
        text_without_spaces,
        r'{"text":"aaaaa","done":false}\n{"text":"Done","done":true}\n',
    )
