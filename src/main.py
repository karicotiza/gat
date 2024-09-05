"""Microservice for dividing text into sentences."""

from re import split
from typing import Annotated

from annotated_types import MaxLen, MinLen
from fastapi import FastAPI
from pydantic import BaseModel


class Settings:
    """App settings."""

    request_min_length: int = 1
    request_max_length: int = 2147483647
    response_min_length: int = 1
    response_max_length: int = 512
    end_of_the_line_characters: list[str] = ['.', '!', '?', ';']


class Splitter:
    """Text splitter."""

    regex: str = ''.join((
        '(?<=[', *Settings.end_of_the_line_characters, r'])\s+',
    ))

    def split_sentences(self, text: str) -> list[str]:
        """Split sentences by any of punctuation marks from settings.

        Args:
            text (str): text.

        Returns:
            list[str]: list of sentences.
        """
        sentences: list[str] = split(self.regex, text)
        sentences = [sentence.strip() for sentence in sentences]
        return [sentence for sentence in sentences if sentence]


class Response(BaseModel):
    """API Response structure."""

    text: list[Annotated[
        str,
        MinLen(Settings.response_min_length),
        MaxLen(Settings.response_max_length),
    ]]


class Request(BaseModel):
    """API Request structure."""

    text: Annotated[
        str,
        MinLen(Settings.request_min_length),
        MaxLen(Settings.request_max_length),
    ]

    def split_sentences(self, splitter: Splitter) -> Response:
        """Split self text to sentences.

        Args:
            splitter (Splitter): splitter instance.

        Returns:
            Response: response structure.
        """
        return Response(text=splitter.split_sentences(self.text))


app: FastAPI = FastAPI()
splitter: Splitter = Splitter()


@app.post('/')
async def text_split(request: Request) -> Response:
    """Text split endpoint.

    Args:
        request (Request): Request structure.

    Returns:
        Response: Response structure.
    """
    return request.split_sentences(splitter)
