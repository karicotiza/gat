FROM python:3.12.5-slim-bookworm

WORKDIR /app

RUN python -m pip install fastapi==0.112.2
RUN python -m pip install uvicorn==0.30.6

COPY ./src/main.py main.py

ENTRYPOINT [ "uvicorn", "main:app", "--host", "0.0.0.0" ]