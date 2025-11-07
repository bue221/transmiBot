from __future__ import annotations

import asyncio
import logging
from typing import Optional

from google.genai import types
from google.adk.agents.llm_agent import LlmAgent, Agent
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from .tools import capture_simit_screenshot, get_current_time
from .prompts import AGENT_DESCRIPTION, AGENT_INSTRUCTION
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# This agent is used to test with agent development kit web interface
root_agent = Agent(
    model=settings.google_agent_model,
    name="root_agent",
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    tools=[get_current_time, capture_simit_screenshot],
)

#### MAIN AGENT CODE ####

APP_NAME = "agents"
USER_ID = "1234"
SESSION_ID = "session1234"

agent = LlmAgent(
    model=settings.google_agent_model,
    name="root_agent",
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
    tools=[get_current_time, capture_simit_screenshot],
)

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


runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)


def _run_agent_sync(query: str) -> str:
    content = types.Content(role="user", parts=[types.Part(text=query)])
    events = runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    )

    final_answer: Optional[str] = None
    for event in events:
        if event.is_final_response() and event.content:
            final_answer = event.content.parts[0].text.strip()

    if final_answer is None:
        raise RuntimeError("Agent did not return a final response")

    return final_answer


async def invoke_agent(query: str) -> str:
    await _ensure_session()
    return await asyncio.to_thread(_run_agent_sync, query)