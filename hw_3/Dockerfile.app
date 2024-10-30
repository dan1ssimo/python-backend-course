FROM python:3.11 AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && apt-get install -y gcc && apt-get install python3-distutils
RUN python -m pip install --upgrade pip

WORKDIR /src
COPY app.py /src/
COPY pyproject.toml /src/
COPY demo_service /src/hw3/demo_service


RUN pip install poetry==1.4.0 && poetry config virtualenvs.create false && poetry install --no-dev

CMD ["uvicorn", "app:app", "--port", "8000", "--host", "0.0.0.0"]