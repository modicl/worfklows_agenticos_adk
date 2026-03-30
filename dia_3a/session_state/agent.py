import asyncio
from dotenv import load_dotenv

load_dotenv()

# Librerias ADK
from typing import Any, Dict

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.tool_context import ToolContext
from google.genai import types


# Helper function that manages a complete conversation session
async def run_session(
    runner_instance: Runner,
    user_queries: list[str] | str = None,
    session_name: str = "default",
):
    print(f"\n ### Session: {session_name}")

    app_name = runner_instance.app_name

    try:
        session = await session_service.create_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )
    except:
        session = await session_service.get_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )

    if user_queries:
        if type(user_queries) == str:
            user_queries = [user_queries]

        for query in user_queries:
            print(f"\nUser > {query}")
            query = types.Content(role="user", parts=[types.Part(text=query)])

            async for event in runner_instance.run_async(
                user_id=USER_ID, session_id=session.id, new_message=query
            ):
                if event.content and event.content.parts:
                    if (
                        event.content.parts[0].text != "None"
                        and event.content.parts[0].text
                    ):
                        print(f"{MODEL_NAME} > ", event.content.parts[0].text)
    else:
        print("No queries!")


# Retry configuration
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# Define scope levels for state keys (following best practices)
USER_NAME_SCOPE_LEVELS = ("temp", "user", "app")


# This demonstrates how tools can write to session state using tool_context.
# The 'user:' prefix indicates this is user-specific data.
def save_userinfo(
    tool_context: ToolContext, user_name: str, country: str
) -> Dict[str, Any]:
    """
    Tool to record and save user name and country in session state.

    Args:
        user_name: The username to store in session state
        country: The name of the user's country
    """
    tool_context.state["name"] = user_name
    tool_context.state["country"] = country

    return {"status": "success"}


# This demonstrates how tools can read from session state.
def retrieve_userinfo(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool to retrieve user name and country from session state.
    """
    # Read from session state
    user_name = tool_context.state.get("name", "Username not found")
    country = tool_context.state.get("country", "Country not found")

    return {"status": "success", "user_name": user_name, "country": country}


print("✅ Tools created.")

# Configuration
APP_NAME = "default"
USER_ID = "default"
MODEL_NAME = "gemini-2.5-flash-lite"

# Create an agent with session state tools
root_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="text_chat_bot",
    description="A text chatbot that remembers user info across the session.",
    instruction="""You are a helpful chatbot.
    - When the user provides their name or country, ALWAYS call `save_userinfo` to store it.
    - When the user asks about their name or country, ALWAYS call `retrieve_userinfo` to fetch it from session state.
    - Never guess or make up the user's name or country — always use the tools.
    """,
    tools=[save_userinfo, retrieve_userinfo],
)

# Set up session service and runner
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, session_service=session_service, app_name="default")

print("✅ Agent with session state tools initialized!")

# Test conversation demonstrating session state

async def main():
    await run_session(
    runner,
    [
        "Hi there, how are you doing today? What is my name?",  # Agent shouldn't know the name yet
        "My name is Sam. I'm from Poland.",  # Provide name - agent should save it
        "What is my name? Which country am I from?",  # Agent should recall from session state
    ],
    "state-demo-session",
    )

# Retrieve the session and inspect its state
async def inspect_data():
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="state-demo-session"
    )

    print("Session State Contents:")
    print(session.state)
    print("\n🔍 Notice the 'user:name' and 'user:country' keys storing our data!")

# Start a completely new session - the agent won't know our name

async def run_new_session():
    await run_session(
        runner,
        ["Hi there, how are you doing today? What is my name?"],
        "new-isolated-session",
    )

# Check the state of the new session
async def inspect_new_data():
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="new-isolated-session"
    )

    print("New Session State:")
    print(session.state)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(inspect_data())
    asyncio.run(run_new_session())
    asyncio.run(inspect_new_data())