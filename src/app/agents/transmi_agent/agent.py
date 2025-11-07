from google.adk.agents.llm_agent import Agent

from .tools import capture_simit_screenshot, get_current_time
from app.config import get_settings

settings = get_settings()

root_agent = Agent(
    model=settings.google_agent_model,
    name='root_agent',
    description=(
        "Provides the current time in a city and can capture Simit account status screenshots."
    ),
    instruction=(
        "You are a helpful assistant that can check the time in a city and capture the Simit "
        "account status screenshot for a given vehicle plate. Use 'get_current_time' for time "
        "queries and 'capture_simit_screenshot' for screenshot requests."
    ),
    tools=[get_current_time, capture_simit_screenshot],
)
