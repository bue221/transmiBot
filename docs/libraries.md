# Bibliotecas y Servicios

| Biblioteca / Servicio | Uso principal | Consideraciones |
| --------------------- | ------------- | --------------- |
| `python-telegram-bot` (>=22.5) | Construye la `Application`, gestiona comandos, polling y webhooks. | Requiere `TELEGRAM_BOT_TOKEN`. Ajustar `TELEGRAM_ALLOWED_UPDATES` para limitar tráfico. |
| `google-adk` (>=0.5.0) | Proporciona `Runner`, `LlmAgent` y sesión in-memory para ejecutar agentes Gemini. | El runner necesita `app_name` alineado con la ruta de los agentes. Configurar `GOOGLE_API_KEY` y `GOOGLE_AGENT_MODEL`. |
| `pydantic` / `pydantic-settings` | Validación y gestión de configuración (`Settings`). | Normaliza valores, soporta `.env`. Errores de parsing se traducen en `ConfigurationError` en tiempo de arranque. |
| `playwright` | Automatiza la navegación web para capturar el estado de Simit. | Instalar navegadores (`playwright install chromium`). Maneja timeouts y excepciones específicas (`PlaywrightTimeoutError`). |
| `asyncio` | Ejecuta tareas concurrentes: creación de sesiones ADK y delegación a `to_thread`. | Evitar `asyncio.run` dentro del handler (ya corregido). |
| `logging` | Observabilidad homogénea. | Configuración centralizada via `configure_logging()`. |

## Variables de Entorno Clave

| Variable | Descripción |
| -------- | ----------- |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram. |
| `GOOGLE_API_KEY` | API key para acceder a Gemini a través del ADK. |
| `GOOGLE_AGENT_MODEL` | Modelo de LLM a usar (por defecto `gemini-2.5-flash`). |
| `TELEGRAM_WEBHOOK_URL` | URL pública para webhook (opcional). |
| `TELEGRAM_ALLOWED_UPDATES` | Lista separada por comas de tipos de update aceptados. |
| `APP_LOG_LEVEL` | Nivel de logging (`INFO`, `DEBUG`, etc.). |
| `PORT` | Puerto cuando se usa webhook (por defecto 8080). |

## Dependencias del sistema

- Playwright requiere librerías de sistema para Chromium (fuentes, dependencias
  de sandbox). En macOS suele bastar con `playwright install chromium`; en
  Linux revisar la documentación oficial.
- Para despliegues Docker, ver `Dockerfile` y asegurarse de instalar los
  paquetes listados en `playwright install-deps`.

## Servicios externos

- **Telegram Bot API**: canal de entrada/salida de mensajes. El bot puede
  operar en modo webhook o polling.
- **Portal Simit**: fuente de datos para el estado de cuenta; la herramienta
  `capture_simit_screenshot` navega hacia `https://www.fcm.org.co/simit`. |

