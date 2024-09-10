"""Utils for tests module."""

from fastapi.testclient import TestClient
from httpx import Response


def check(client: TestClient, before: str, after: str | None = None) -> None:
    """Check output of post request to FastAPI app.

    Args:
        client (TestClient): FastAPI TestClient.
        before (str): input json.
        after (str | None, optional): output json. Defaults to None.

    Raises:
        ValueError: on wrong status code.
        ValueError: on wrong after.
    """
    success_code: int = 200
    response: Response = client.post('/', json={'text': before})

    if response.status_code != success_code:
        raise ValueError('Failed')

    if after and str(response.content)[2:-1] != after:
        raise ValueError('Failed')
