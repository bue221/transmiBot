# Operación y Puesta en Marcha

## Requisitos previos

- Python 3.12 instalado (recomendado gestionar con `uv` o `pyenv`).
- Playwright Chromium (`uv run playwright install chromium`).
- Variables de entorno configuradas (ver `libraries.md`).
- Cuenta de Telegram con bot creado mediante `@BotFather`.

## Configuración local

```shell
uv sync --python 3.12
uv run playwright install chromium
cp .env.example .env  # ajustar credenciales
```

## Ejecución

| Tarea | Comando | Notas |
| ----- | ------- | ----- |
| Ejecutar en modo polling | `uv run python -m app.main` | Usa `TELEGRAM_ALLOWED_UPDATES` y elimina pendientes al iniciar. |
| Levantar interfaz web de ADK | `make adk-web` | Carga el agente definido en `transmi_agent`. |
| Construir contenedor | `make docker-build` | Imagen `transmibot:latest`. |
| Ejecutar contenedor | `make docker-run` | Espera `TELEGRAM_BOT_TOKEN` y `GOOGLE_API_KEY` en el entorno. |

## Webhook vs Polling

- **Webhook**: establecer `TELEGRAM_WEBHOOK_URL` (p.e. usando Cloud Run o
  Ngrok). Ajustar `PORT` y abrir el puerto correspondiente.
- **Polling**: dejar `TELEGRAM_WEBHOOK_URL` vacío. Ideal para desarrollo local.

## Observabilidad y manejo de errores

- Logging estructurado configurable mediante `APP_LOG_LEVEL`.
- `handlers.handle_error` captura excepciones en Telegram y las registra con el
  stack completo.
- `invoke_agent` detecta fallos del runner y regresa un mensaje amigable al
  usuario.
- La herramienta `capture_simit_screenshot` diferencia errores de validación,
  timeout, Playwright e I/O, permitiendo diagnósticos rápidos.
- Las operaciones de base de datos (`app.db.crud`) encapsulan errores en un
  decorador común, garantizando que fallos de escritura o conexión no
  interrumpan el flujo de conversación; los errores se registran y el bot
  continúa operando.

## Operación del CI/CD

- **Workflow de build:** el job `docker-build` en GitHub Actions construye la
  imagen Docker en cada cambio relevante (`main`/`develop`) y sirve como
  “smoke test” del entorno de contenedor.
- **Revisión de fallos:** ante un fallo en el workflow, revisar los logs del
  paso `docker/build-push-action` para identificar problemas en dependencias,
  cambios en `Dockerfile` o binarios de Playwright.
- **Despliegue controlado:** aunque el CI no despliega automáticamente, se
  recomienda utilizar sólo imágenes que hayan pasado por el workflow de build
  para entornos productivos o de staging.

## Consideraciones de rendimiento

- Las operaciones de Playwright pueden tardar varios segundos; se recomienda
  desplegar en entornos con suficiente CPU para navegadores headless.
- Las capturas se almacenan en `var/screenshots`; implementar rotación o
  almacenamiento externo (S3, GCS) para ambientes productivos.
- La base de datos SQLite (`var/transmibot.db`) está pensada para volúmenes
  bajos/medios de uso y para un único contenedor; para escenarios de alta
  concurrencia o múltiples réplicas, se recomienda migrar a un motor externo
  (PostgreSQL, Cloud SQL) manteniendo la misma capa `app.db`.
- `invoke_agent` delega el runner a un hilo (`asyncio.to_thread`) evitando
  bloquear el loop principal de Telegram.

## Pruebas sugeridas

- Pruebas unitarias para `capture_simit_screenshot` usando `pytest` con
  `pytest-asyncio`, mockeando Playwright.
- Pruebas de integración que simulen mensajes de Telegram mediante
  `Application.bot.send_message` en modo `run_polling`.
- Smoke test del agente vía `make adk-web` para validar prompts y tools antes de
  cualquier despliegue.

