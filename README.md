# transmiBot

## Purpose

Telegram chatbot scaffold that delegates conversational responses to a Google ADK agent (Gemini).

## Stack

- Python 3.12, managed with `uv`
- `python-telegram-bot` async dispatcher
- Google Agent Development Kit (ADK) with Gemini model
- Playwright for browser automation (Chromium headless)
- Docker image for deployment

## Prerequisites

- `uv` installed locally (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Telegram bot token (`TELEGRAM_BOT_TOKEN`)
- Gemini API key (`GOOGLE_API_KEY`)

## Local Setup

```bash
uv sync --python 3.12
uv run playwright install
uv run python -m app.main
```

The dedicated `playwright install` step downloads the browser binaries required for the
Simit screenshot tool. See the [Playwright Python introduction](https://playwright.dev/python/docs/intro)
for additional options.

Simit screenshots are stored in `var/screenshots/` with timestamped filenames for traceability.
The automation allows the Simit page to settle for ~7 seconds before capturing the screenshot to
ensure dynamic content has finished loading.
The tool also extracts the textual content of every `.container-fluid` block so the agent can
summarise or analyse the retrieved information.

## Configuration

Create a `.env` file (or export variables) with:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_WEBHOOK_URL=https://example.com/webhook  # optional, fallback to polling
GOOGLE_API_KEY=your-gemini-key
GOOGLE_AGENT_MODEL=gemini-2.5-flash
APP_ENV=development
APP_LOG_LEVEL=INFO
```

## Docker

```bash
docker build -t transmibot:latest .
docker run --rm \
  -e TELEGRAM_BOT_TOKEN \
  -e GOOGLE_API_KEY \
  -p 8080:8080 \
  transmibot:latest
```

If using webhooks, configure your reverse proxy to forward `POST /telegram/webhook` to the container (port 8080).

## Next Steps

- Flesh out domain-specific handlers in `app/telegram/handlers.py`
- Add integration tests that mock the Google ADK agent
- Wire observability (metrics, tracing) if required by production environment
