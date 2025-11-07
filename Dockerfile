FROM python:3.12-slim

ENV UV_VERSION=0.4.10 \
    APP_HOME=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommENDS build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR ${APP_HOME}

COPY pyproject.toml ./

RUN uv sync --no-editable

COPY src ./src
COPY tests ./tests

ENV PYTHONPATH="${APP_HOME}/src"

CMD ["uv", "run", "python", "-m", "app.main"]

