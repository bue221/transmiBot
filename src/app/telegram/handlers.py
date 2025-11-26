from __future__ import annotations

import asyncio
import logging

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.agents.transmi_agent.agent import invoke_agent
from app.db.crud import (
    get_or_create_user_by_telegram_id,
    log_interaction_by_telegram_id,
)

logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        logger.warning("Received /start without message: %s", update)
        return

    # Pedimos el número de teléfono usando el teclado de Telegram para poder usarlo como ID.
    contact_button = KeyboardButton(text="Compartir mi teléfono 📱", request_contact=True)
    reply_markup = ReplyKeyboardMarkup(
        [[contact_button]], resize_keyboard=True, one_time_keyboard=True
    )

    await update.message.reply_text(
        "👋 ¡Hola! Soy *TransmiBot*, tu asistente de movilidad en Colombia.\n\n"
        "🚗 Puedo ayudarte a:\n"
        "• Calcular rutas con información de tráfico en tiempo real\n"
        "• Buscar lugares cercanos (gasolineras, parqueaderos, etc.)\n"
        "• Consultar el estado de multas en Simit por placa de vehículo\n\n"
        "Para personalizar mejor tu experiencia, puedes compartir tu número de teléfono "
        "tocando el botón de abajo (opcional).",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ *Comandos disponibles*\n"
        "• /start – Mensaje de bienvenida y resumen del bot.\n"
        "• /help – Muestra esta lista de comandos.\n\n"
        "También puedes escribirme directamente para: calcular rutas con tráfico,"
        " buscar lugares cercanos o consultar el estado de multas de tu vehículo en Simit.",
        parse_mode="Markdown",
    )


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when user shares their phone number."""
    if update.message is None or update.message.contact is None:
        return

    contact = update.message.contact
    phone_number = contact.phone_number
    user = update.effective_user
    telegram_id = user.id if user else None

    if telegram_id:
        # Register/update user with phone number
        try:
            await asyncio.to_thread(
                get_or_create_user_by_telegram_id,
                telegram_id,
                phone_number=phone_number,
                username=user.username if user else None,
                first_name=user.first_name if user else None,
                last_name=user.last_name if user else None,
            )
            await update.message.reply_text(
                "✅ ¡Gracias por compartir tu número! "
                "Ahora puedo personalizar mejor tu experiencia."
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register user with phone number")
            await update.message.reply_text(
                "⚠️ Hubo un problema al registrar tu número. "
                "Puedes seguir usando el bot normalmente."
            )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception in Telegram handler", exc_info=context.error)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        logger.warning("Received text handler update without message: %s", update)
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    telegram_id = user.id if user else None

    if not telegram_id:
        logger.warning("Received message without telegram_id: %s", update)
        return

    # Intentamos obtener el teléfono desde el contacto compartido o desde el contexto.
    phone_number: str | None = None
    if update.message.contact and update.message.contact.phone_number:
        phone_number = update.message.contact.phone_number

    # Siempre registramos/creamos el usuario usando telegram_id
    try:
        await asyncio.to_thread(
            get_or_create_user_by_telegram_id,
            telegram_id,
            phone_number=phone_number,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
            last_name=user.last_name if user else None,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to upsert user")

    # Registramos el mensaje del usuario
    try:
        message_text = update.message.text or ""
        await asyncio.to_thread(
            log_interaction_by_telegram_id,
            telegram_id,
            message_text,
            role="user",
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log user interaction")

    status_message = await update.message.reply_text("Procesando ⏳")

    stop_event = asyncio.Event()

    async def animate_status_message() -> None:
        # Small delay before starting animation to avoid immediate edit after creation
        await asyncio.sleep(0.5)
        
        animation_frames = ["⏳", "⌛"]
        frame_index = 1  # Start at 1 since we already showed ⏳
        last_text = "Procesando ⏳"

        while not stop_event.is_set():
            try:
                new_text = f"Procesando {animation_frames[frame_index]}"
                # Only edit if text actually changed to avoid 400 errors
                if new_text != last_text:
                    await status_message.edit_text(new_text)
                    last_text = new_text
                frame_index = (frame_index + 1) % len(animation_frames)
                await asyncio.sleep(1.5)  # Slightly longer delay to reduce edit frequency
            except BadRequest as exc:
                error_str = str(exc).lower()
                # Telegram returns 400 for "message is not modified" or other edit failures
                if "message is not modified" in error_str or "bad request" in error_str:
                    # Silently continue - message might have been edited elsewhere or is unchanged
                    await asyncio.sleep(1)  # Wait before next attempt
                else:
                    logger.debug("Error animando mensaje (non-critical): %s", exc)
                    await asyncio.sleep(1)
            except Exception as exc:  # noqa: BLE001
                # Log but don't stop - let stop_event handle termination
                logger.debug("Error inesperado en animate_message (non-critical): %s", exc)
                await asyncio.sleep(1)  # Wait before retrying to avoid tight loop

    async def send_typing_action() -> None:
        while not stop_event.is_set():
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                await asyncio.sleep(4)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error en keep_typing_action: %s", exc)
                return

    animate_task = asyncio.create_task(animate_status_message())
    typing_task = asyncio.create_task(send_typing_action())

    # Use Telegram tools with database logging (always enabled now)
    agent_stream = invoke_agent(
        update.message.text,
        telegram_id=telegram_id,
        use_telegram_tools=True,
    )

    try:
        first_response = await agent_stream.__anext__()
    except StopAsyncIteration:
        stop_event.set()
        animate_task.cancel()
        typing_task.cancel()
        await asyncio.gather(animate_task, typing_task, return_exceptions=True)
        await agent_stream.aclose()
        await status_message.edit_text(
            "Lo siento, ocurrió un error al consultar al agente. Inténtalo de nuevo más tarde."
        )
        logger.error("Agent stream completed without responses")
        return
    except Exception:
        stop_event.set()
        animate_task.cancel()
        typing_task.cancel()
        await asyncio.gather(animate_task, typing_task, return_exceptions=True)
        logger.exception("Agent invocation failed before first response")
        await status_message.edit_text(
            "Lo siento, ocurrió un error al consultar al agente. Inténtalo de nuevo más tarde."
        )
        await agent_stream.aclose()
        return

    stop_event.set()
    animate_task.cancel()
    typing_task.cancel()
    await asyncio.gather(animate_task, typing_task, return_exceptions=True)
    
    # Small delay to ensure animation task has fully stopped before editing
    await asyncio.sleep(0.2)

    # Guardamos la primera respuesta del asistente
    try:
        await asyncio.to_thread(
            log_interaction_by_telegram_id,
            telegram_id,
            first_response,
            role="assistant",
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log assistant first response")

    try:
        await status_message.edit_text(first_response)
    except BadRequest as exc:
        # If edit fails (e.g., message was deleted or already modified), send new message
        error_str = str(exc).lower()
        if "message is not modified" in error_str or "bad request" in error_str:
            logger.debug("Could not edit status message, sending new message instead")
            await update.message.reply_text(first_response)
        else:
            raise

    try:
        async for response_text in agent_stream:
            try:
                await context.bot.send_message(chat_id=chat_id, text=response_text)
                # Guardamos cada respuesta adicional del asistente
                try:
                    await asyncio.to_thread(
                        log_interaction_by_telegram_id,
                        telegram_id,
                        response_text,
                        role="assistant",
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to log assistant follow-up response")
            except Exception:
                logger.warning(
                    "Failed to send follow-up agent response",
                    exc_info=True,
                )
    except Exception:
        logger.exception("Agent invocation failed while streaming responses")
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Lo siento, ocurrió un error al consultar al agente. "
                "Inténtalo de nuevo más tarde."
            ),
        )
    finally:
        stop_event.set()
        await agent_stream.aclose()