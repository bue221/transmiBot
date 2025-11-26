from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from typing import Optional

from google.adk.agents.llm_agent import Agent, LlmAgent
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import get_settings

from .prompts import AGENT_DESCRIPTION, AGENT_INSTRUCTION
from .tools import (
    capture_simit_screenshot,
    get_current_time,
    tomtom_find_nearby_services,
    tomtom_find_nearby_services_by_address,
    tomtom_geocode_address,
    tomtom_route_with_traffic,
)
from .tools_telegram import (
    capture_simit_screenshot as telegram_capture_simit_screenshot,
)
from .tools_telegram import (
    set_user_context,
)
from .tools_telegram import (
    tomtom_find_nearby_services as telegram_tomtom_find_nearby_services,
)
from .tools_telegram import (
    tomtom_find_nearby_services_by_address as telegram_tomtom_find_nearby_services_by_address,
)
from .tools_telegram import (
    tomtom_geocode_address as telegram_tomtom_geocode_address,
)
from .tools_telegram import (
    tomtom_route_with_traffic as telegram_tomtom_route_with_traffic,
)

logger = logging.getLogger(__name__)

settings = get_settings()

# Ensure GOOGLE_API_KEY is available in the environment for Google ADK
# Google ADK reads the API key from the environment variable automatically
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

# This agent is used to test with agent development kit web interface
root_agent = Agent(
    model=settings.google_agent_model,
    name="root_agent",
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    tools=[
        get_current_time,
        capture_simit_screenshot,
        tomtom_route_with_traffic,
        tomtom_find_nearby_services,
        tomtom_geocode_address,
        tomtom_find_nearby_services_by_address,
    ],
)

#### MAIN AGENT CODE ####

APP_NAME = "agents"
USER_ID = "1234"
SESSION_ID = "session1234"

session_service = InMemorySessionService()


async def _ensure_session() -> None:
    try:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        logger.info(
            "Created session %s for app %s and user %s",
            SESSION_ID,
            APP_NAME,
            USER_ID,
        )
    except AlreadyExistsError:
        logger.debug(
            "Session %s for app %s and user %s already exists",
            SESSION_ID,
            APP_NAME,
            USER_ID,
        )

# Base agent for ADK testing (simple tools without database logging)
agent = LlmAgent(
    model=settings.google_agent_model,
    name="root_agent",
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    tools=[
        capture_simit_screenshot,
        tomtom_route_with_traffic,
        tomtom_find_nearby_services,
        tomtom_geocode_address,
        tomtom_find_nearby_services_by_address,
    ],
)

# Separate agent for Telegram with database logging tools
telegram_agent = LlmAgent(
    model=settings.google_agent_model,
    name="root_agent",
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    tools=[
        telegram_capture_simit_screenshot,
        telegram_tomtom_route_with_traffic,
        telegram_tomtom_find_nearby_services,
        telegram_tomtom_geocode_address,
        telegram_tomtom_find_nearby_services_by_address,
    ],
)

runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)
telegram_runner = Runner(agent=telegram_agent, app_name=APP_NAME, session_service=session_service)


def _run_agent_sync(
    query: str,
    *,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[Optional[str]],
    phone_number: str | None = None,
    use_telegram_tools: bool = False,
) -> None:
    # Set user context for Telegram tools if phone_number is provided
    if use_telegram_tools and phone_number:
        set_user_context(phone_number)

    content = types.Content(role="user", parts=[types.Part(text=query)])
    active_runner = telegram_runner if use_telegram_tools else runner
    events = active_runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    )

    final_answer: Optional[str] = None

    def _emit(message: str) -> None:
        future = asyncio.run_coroutine_threadsafe(queue.put(message), loop)
        future.result()

    try:
        previous_message: Optional[str] = None

        for event in events:
            event_content = getattr(event, "content", None)
            if event_content is None:
                continue

            parts = getattr(event_content, "parts", [])
            text_segments: list[str] = []

            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str):
                    normalized_text = part_text.strip()
                    if normalized_text:
                        text_segments.append(normalized_text)

            if not text_segments:
                continue

            message_text = "\n\n".join(text_segments)

            if previous_message != message_text:
                _emit(message_text)
                previous_message = message_text

            if event.is_final_response():
                final_answer = message_text

        if final_answer is None:
            raise RuntimeError("Agent did not return a final response")

    finally:
        asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()


async def invoke_agent(
    query: str, phone_number: str | None = None, use_telegram_tools: bool = False
) -> AsyncIterator[str]:
    """Invoke the agent with optional phone_number for database logging.

    Args:
        query: User's message text.
        phone_number: Optional phone number for database logging (Telegram only).
        use_telegram_tools: If True, use tools with database logging. Default False for ADK testing.

    Returns:
        Async iterator of response text chunks.
    """
    await _ensure_session()

    loop = asyncio.get_running_loop()
    message_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
    worker_task = asyncio.create_task(
        asyncio.to_thread(
            _run_agent_sync,
            query,
            loop=loop,
            queue=message_queue,
            phone_number=phone_number,
            use_telegram_tools=use_telegram_tools,
        )
    )

    try:
        while True:
            item = await message_queue.get()
            if item is None:
                break
            yield item
    finally:
        await worker_task