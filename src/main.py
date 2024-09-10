"""Microservice for dividing text into sentences."""

from dataclasses import dataclass
from typing import Annotated, ClassVar, Generator

from annotated_types import Ge, Le, MaxLen, MinLen
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class Settings(BaseModel):
    """App settings."""

    request_min_length: ClassVar[int] = 1
    request_max_length: ClassVar[int] = 4194304
    response_min_length: ClassVar[int] = 1
    response_max_length: ClassVar[int] = 256

    media_type: ClassVar[str] = 'application/json'


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


class ResponseBody(BaseModel):
    """Response body."""

    text: Annotated[
        str,
        MinLen(Settings.response_min_length),
        MaxLen(Settings.response_max_length),
    ]

    done: bool = False


class RequestBody(BaseModel):
    """Request body."""

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
            response: ResponseBody = ResponseBody(text=sentence)
            yield ''.join((response.model_dump_json(), '\n'))

        response = ResponseBody(text=' ', done=True)
        yield ''.join((response.model_dump_json(), '\n'))


app: FastAPI = FastAPI()
splitter: TextSplitter = TextSplitter()


@app.post(
    '/',
    response_class=StreamingResponse,
    responses={
        200: {
            'description': 'Stream of ResponseBody',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'array',
                        'items': ResponseBody.model_json_schema(),
                    },
                },
            },
        },
    },
    response_model=ResponseBody,
)
async def text_split(request: RequestBody) -> StreamingResponse:
    """# Text split endpoint.

    The endpoint accepts text as input and divides it into segments, no longer
    than ResponseBody.text max length, but as close as possible.

    This can be useful for processing text in small batches, for example,
    for synthesizing text in streaming mode.

    Rules for dividing text:
    1. If one or more complete sentences can fit into this number of max\
        characters, it places the entire sentence in the segment.
    2. If the full sentence does not fit into this number of max characters,\
        then it is divided by internal punctuation marks and the largest part\
        is placed in the segment.
    3. If there are no punctuation marks in the text, it is divided by spaces,\
        and the largest possible part is placed in the segment.
    4. If there are no spaces in the text, then the text is divided into\
        segments according to the number of characters.

    Args:
        request (RequestBody): Request body, details below.

    Returns:
        StreamingResponse: Response body stream, details below.
    """
    return request.response(splitter)
