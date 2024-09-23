"""Text split microservice."""

from typing import Annotated, Generator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings."""

    request_min_length: int = 1
    request_max_length: int = 4194304
    response_min_length: int = 1
    response_max_length: int = 256

    media_type: str = 'application/x-ndjson'


settings: Settings = Settings()


class RequestBody(BaseModel):
    """Request body."""

    text: Annotated[str, StringConstraints(
        strip_whitespace=True,
        min_length=settings.request_min_length,
        max_length=settings.request_max_length,
    )]


class ResponseBody(BaseModel):
    """Response body."""

    text: Annotated[str, StringConstraints(
        strip_whitespace=True,
        min_length=settings.response_min_length,
        max_length=settings.response_max_length,
    )]

    done: bool = False


class Sentence(BaseModel):
    """Sentence structure for TextSplitter."""

    text: str
    end: int


class Cursor(BaseModel):
    """Splitter memory structure."""

    index: int

    terminal_at: int | None = None
    internal_at: int | None = None
    space_at: int | None = None

    is_terminal: bool = False
    is_internal: bool = False
    is_space: bool = False

    character: str = ''


class Service:
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
        end: int = settings.response_max_length

        while True:
            if start == text_length:
                yield self._string_to_stream_response()
                break

            chunk_of_text: str = text[start: end]
            sentence: Sentence = self._extract_sentence(chunk_of_text)
            start = start + sentence.end
            end = start + settings.response_max_length

            yield self._string_to_stream_response(sentence.text.strip())

    def _extract_sentence(self, text: str) -> Sentence:
        memory: Cursor = Cursor(index=(len(text) - 1))

        while memory.index != -1:
            memory.character = text[memory.index]
            self._check_character(memory)

            if memory.terminal_at is not None:
                break

            memory.index -= 1

        return self._process_points(text, memory)

    def _check_character(self, memory: Cursor) -> None:
        if memory.character in self._terminal:
            memory.terminal_at = memory.index

        elif memory.character in self._internal and memory.internal_at is None:
            memory.internal_at = memory.index

        elif memory.character in self._space and memory.space_at is None:
            memory.space_at = memory.index

    def _process_points(self, text: str, memory: Cursor) -> Sentence:
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

    def _string_to_stream_response(self, sentence: str = '') -> str:
        """Format strings to be sent using streaming.

        Args:
            sentence (str): sentence.

        Returns:
            str: Stream ready sentence.
        """
        if sentence:
            response: ResponseBody = ResponseBody(text=sentence)
            return ''.join((response.model_dump_json(), '\n'))

        response = ResponseBody(text='Done', done=True)
        return ''.join((response.model_dump_json(), '\n'))


service: Service = Service()
app: FastAPI = FastAPI()


@app.post(
    '/',
    response_class=StreamingResponse,
    responses={
        200: {
            'description': 'Stream of ResponseBody',
            'content': {
                'application/x-ndjson': {
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
    stream: Generator[str, None, None] = service.split(request.text)
    return StreamingResponse(stream, media_type=settings.media_type)
