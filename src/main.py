"""Microservice for dividing text into sentences."""

from re import split
from typing import Annotated

from annotated_types import MaxLen, MinLen
from fastapi import FastAPI
from pydantic import BaseModel
from pysbd import Segmenter  # type: ignore
from uvicorn import run


class Settings:
    request_min_length: int = 1
    request_max_length: int = 2147483647
    response_min_length: int = 1
    response_max_length: int = 512
    end_of_the_line_characters: list[str] = ['.', '!', '?', ';']

    regex: str = ''.join(('(?<=[', *end_of_the_line_characters, r'])\s+'))

class Response(BaseModel):
    text: list[Annotated[
        str,
        MinLen(Settings.response_min_length),
        MaxLen(Settings.response_max_length),
    ]]


class Request(BaseModel):
    text: Annotated[
        str,
        MinLen(Settings.request_min_length),
        MaxLen(Settings.request_max_length),
    ]

    def split_sentences(self) -> Response:
        sentences: list[str] = split(Settings.regex, self.text)
        sentences = [sentence.strip() for sentence in sentences]
        sentences = [sentence for sentence in sentences if sentence]
        return Response(text=sentences)


app: FastAPI = FastAPI()


@app.post('/')
async def text_split(request: Request) -> Response:
    return request.split_sentences()

if __name__ == '__main__':
    run('main:app')
