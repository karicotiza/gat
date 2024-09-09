"""Microservice for dividing text into sentences."""

from dataclasses import dataclass
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


@dataclass(slots=True)
class SplitterMemory:
    """Splitter memory structure."""

    cursor: int

    terminal_at: int | None = None
    internal_at: int | None = None
    space_at: int | None = None

    is_terminal: bool = False
    is_internal: bool = False
    is_space: bool = False

    character: str = ''


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
        memory: SplitterMemory = SplitterMemory(len(text) - 1)

        while memory.cursor != -1:
            memory.character = text[memory.cursor]
            self._check_character(memory)

            if memory.terminal_at is not None:
                break

            memory.cursor -= 1

        return self._process_points(text, memory)

    def _check_character(self, memory: SplitterMemory) -> None:
        if memory.character in self._terminal:
            memory.terminal_at = memory.cursor

        elif memory.character in self._internal and memory.internal_at is None:
            memory.internal_at = memory.cursor

        elif memory.character in self._space and memory.space_at is None:
            memory.space_at = memory.cursor

    def _process_points(self, text: str, memory: SplitterMemory) -> Sentence:
        if memory.terminal_at:
            text = text[:memory.terminal_at + 1]
            end: int = memory.terminal_at + 1

        elif memory.internal_at:
            text = text[:memory.internal_at + 1]
            end = memory.internal_at + 1

        elif memory.space_at:
            text = text[:memory.space_at]
            end = memory.space_at + 1

        else:
            end = len(text)

        return Sentence(text=text, end=end)


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
