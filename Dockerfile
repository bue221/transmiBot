FROM python:3.12-slim

ENV UV_VERSION=0.4.10 \
    APP_HOME=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR ${APP_HOME}

COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync --no-editable
RUN uv run playwright install --with-deps chromium

COPY src ./src

ENV PYTHONPATH="${APP_HOME}/src"
EXPOSE 8080

CMD ["uv", "run", "python", "-m", "app.main"]

