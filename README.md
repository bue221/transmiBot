# TransmiBot

<img width="522" height="616" alt="image" src="https://github.com/user-attachments/assets/df0a401f-248b-4988-abd2-fde0248acf36" />

## Propósito

TransmiBot es un chatbot para Telegram que delega sus respuestas a un agente de Google ADK (Gemini) para asistir con temas de movilidad en Colombia.

## Stack

- Python 3.12, administrado con `uv`
- Despachador asíncrono `python-telegram-bot`
- Google Agent Development Kit (ADK) con modelo Gemini
- Playwright para automatización de navegador (Chromium headless)
- Imagen Docker lista para despliegue

## Requisitos previos

- `uv` instalado localmente (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Token del bot de Telegram (`TELEGRAM_BOT_TOKEN`)
- API Key de Gemini (`GOOGLE_API_KEY`)

## Configuración local

```bash
uv sync --python 3.12
uv run playwright install
uv run python -m app.main
```

El paso `playwright install` descarga los binarios del navegador necesarios para la herramienta de capturas Simit. Consulta la [introducción de Playwright para Python](https://playwright.dev/python/docs/intro) si necesitas más opciones.

Las capturas de Simit se guardan en `var/screenshots/` con nombres timestamp para trazabilidad. La automatización espera ~7 segundos antes de capturar la imagen para asegurar que el contenido dinámico haya terminado de cargar. La herramienta también extrae el texto de cada bloque `.container-fluid` para que el agente pueda resumir o analizar la información.

## Configuración por entorno

Crea un archivo `.env` (o exporta variables) con:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_WEBHOOK_URL=https://example.com/webhook  # opcional, usa polling si se omite
GOOGLE_API_KEY=tu-gemini-key
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

Si usas webhooks, configura tu reverse proxy para dirigir `POST /telegram/webhook` hacia el contenedor (puerto 8080).

## Próximos pasos sugeridos

- Ampliar los handlers específicos del dominio en `app/telegram/handlers.py`.
- Añadir pruebas de integración que simulen al agente de Google ADK.
- Integrar observabilidad (métricas, tracing) según las necesidades del entorno productivo.
