# Módulos y Responsabilidades

| Módulo | Responsabilidad principal | Dependencias clave | Notas de manejo de errores |
| ------ | ------------------------- | ------------------- | -------------------------- |
| `app.config` | Carga y valida configuraciones usando `pydantic-settings`. | `pydantic`, variables de entorno. | Normaliza listas (`TELEGRAM_ALLOWED_UPDATES`) y lanza `ValueError` ante formatos inválidos. |
| `app.logging_config` | Configura logging estructurado según el nivel definido en entorno. | `logging`, `get_settings()`. | Permite ajustar nivel sin modificar código. |
| `app.exceptions` | Define jerarquía de errores específicos del dominio. | N/A | Facilita captura diferenciada en `main`. |
| `app.main` | Punto de entrada: inicia logging, crea la aplicación de Telegram y gestiona webhook/polling. | `python-telegram-bot`, `app.telegram.bot`, `app.config`. | Captura `ExternalServiceError` y excepciones inesperadas (envolviéndolas en `ConfigurationError`). |
| `app.telegram.bot` | Construye `Application` registrando comandos y handler de texto. | `python-telegram-bot`. | Centraliza registro de handlers para mejorar testabilidad. |
| `app.telegram.handlers` | Gestiona comandos `/start`, `/help`, errores y mensajes libres. | `invoke_agent`. | Valida `update.message`, captura fallos del agente y devuelve mensaje amigable. |
| `app.agents.transmi_agent.agent` | Configura agentes ADK y runner, garantiza la sesión y expone `invoke_agent`. | `google-adk`, `asyncio`, `prompts`, `tools`. | Reintenta creación de sesión (idempotente) y transforma errores en `RuntimeError` controlada. |
| `app.agents.transmi_agent.prompts` | Contiene descripción e instrucciones del agente en español, referencias a herramientas. | N/A | Guía al agente para comunicar errores y mantener idioma correcto. |
| `app.agents.transmi_agent.tools` | Implementa `get_current_time` y `capture_simit_screenshot`. | `playwright`, `logging`, `pathlib`. | Devuelve diccionarios estructurados, diferencia errores de validación, timeout, I/O y otros. |

## Servicios auxiliares

- `var/screenshots/`: almacenamiento local de las capturas Simit generadas por
  Playwright. Ideal montarlo como volumen persistente en producción.
- `Makefile`: atajos para `uv sync`, ejecución local y comandos Docker.
- `Dockerfile`: empaqueta la aplicación con Playwright (revisar requisitos de
  dependencias del navegador al desplegar).

## Interacciones entre módulos

```mermaid
flowchart TD
    Main[app.main]
    Bot[app.telegram.bot]
    Handlers[app.telegram.handlers]
    Agent[transmi_agent.agent]
    Prompts[prompts]
    Tools[tools]
    Config[app.config]

    Main -->|lee configuración| Config
    Main --> Bot
    Bot --> Handlers
    Handlers -->|await| Agent
    Agent --> Prompts
    Agent --> Tools
```

- Los módulos se comunican a través de funciones claramente tipadas (`invoke_agent`).
- Las herramientas pueden ejecutarse de forma asíncrona dentro del runner, pero
  exponen interfaces síncronas o `async` según lo requiera el ADK.

