"""Microservice for dividing text into sentences."""

from typing import Annotated, Generator

from annotated_types import Ge, Le, MaxLen, MinLen
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class Settings:
    """App settings."""

    request_min_length: int = 1
    request_max_length: int = 2147483647
    response_min_length: int = 1
    response_max_length: int = 256

    media_type: str = 'application/json'


class Sentence(BaseModel):
    """Sentence structure for TextSplitter."""

    text: Annotated[
        str,
        MinLen(Settings.response_min_length),
        MaxLen(Settings.response_max_length),
    ]
    end: Annotated[
        int,
        Ge(Settings.response_min_length),
        Le(Settings.response_max_length),
    ]


class TextSplitter:
    """Splits text to sentences longer shorter than response_max_length + 1."""

    _terminal: list[str] = ['.', '!', '?', ';']
    _internal: list[str] = ['-', ':', ',']
    _space: list[str] = ['\n', '\r', '\t', '\f', ' ']

    def split(self, text: str) -> Generator[str, None, None]:
        """Split long text to sentences shorter response_max_length + 1.

        Args:
            text (str): long text

        Yields:
            Generator[str, None, None]: stream of sentences.
        """
        text_length: int = len(text)
        start: int = 0
        end: int = Settings.response_max_length

        while True:
            if end > text_length:
                end = text_length
                yield self._extract_sentence(text[start: end]).text
                break

            chunk_of_text: str = text[start: end]
            sentence: Sentence = self._extract_sentence(chunk_of_text)
            start = start + sentence.end
            end = start + Settings.response_max_length

            yield sentence.text

    def _extract_sentence(self, text: str) -> Sentence:
        cursor: int = len(text) - 1
        internal_at: int | None = None
        space_at: int | None = None

        while True:
            character: str = text[cursor]

            if character in self._terminal:
                return Sentence(text=text[:cursor + 1], end=cursor + 1)

            elif character in self._internal and internal_at is None:
                internal_at = cursor

            elif character in self._space and space_at is None:
                space_at = cursor

            cursor -= 1

            if cursor == -1:
                break

        if internal_at:
            return Sentence(text=text[:internal_at + 1], end=internal_at + 1)

        elif space_at:
            return Sentence(text=text[:space_at], end=space_at + 1)

        return Sentence(text=text, end=len(text))


class Response(BaseModel):
    """API Response structure."""

    text: Annotated[
        str,
        MinLen(Settings.response_min_length),
        MaxLen(Settings.response_max_length),
    ]


class Request(BaseModel):
    """API Request structure."""

    text: Annotated[
        str,
        MinLen(Settings.request_min_length),
        MaxLen(Settings.request_max_length),
    ]

    def response(self, splitter: TextSplitter) -> StreamingResponse:
        """Get response, as stream.

        Args:
            splitter (TextSplitter): text splitter.

        Returns:
            StreamingResponse: stream of data
        """
        return StreamingResponse(
            self._split_sentences(splitter),
            media_type=Settings.media_type,
        )

    def _split_sentences(
        self, splitter: TextSplitter,
    ) -> Generator[str, None, None]:
        for sentence in splitter.split(self.text):
            response: Response = Response(text=sentence)
            yield ''.join((response.model_dump_json(), '\n'))


app: FastAPI = FastAPI()
splitter: TextSplitter = TextSplitter()


@app.post('/')
async def text_split(request: Request) -> StreamingResponse:
    """Text split endpoint.

    Args:
        request (Request): Request structure.

    Returns:
        StreamingResponse: stream of response structure.
    """
    return request.response(splitter)
