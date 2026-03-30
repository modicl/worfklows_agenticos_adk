import asyncio
from dotenv import load_dotenv

load_dotenv()

# Librerias ADK
from typing import Any, Dict

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import load_memory
from google.adk.tools import preload_memory
from google.adk.runners import Runner
from google.adk.tools.tool_context import ToolContext
from google.genai import types


# Helper functions

async def run_session(
    runner_instance: Runner, user_queries: list[str] | str, session_id: str = "default"
):
    """Helper function to run queries in a session and display responses."""
    print(f"\n### Session: {session_id}")

    # Create or retrieve session
    try:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
    except:
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )

    # Convert single query to list
    if isinstance(user_queries, str):
        user_queries = [user_queries]

    # Process each query
    for query in user_queries:
        print(f"\nUser > {query}")
        query_content = types.Content(role="user", parts=[types.Part(text=query)])

        # Stream agent response
        async for event in runner_instance.run_async(
            user_id=USER_ID, session_id=session.id, new_message=query_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text and text != "None":
                    print(f"Model: > {text}")

# Callback para ir guardando memoria
async def auto_save_to_memory(callback_context):
    """Automatically save session to memory after each agent turn."""
    await callback_context._invocation_context.memory_service.add_session_to_memory(
        callback_context._invocation_context.session # accede al contexto que tiene el runner y guarda la sesion a traves de add_session_to_memory
    )


print("✅ Callback created.")

print("✅ Helper functions defined.")

retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

# Memory Service

memory_service = (
    InMemoryMemoryService()
)  # ADK's built-in Memory Service for development and testing


# Define constants used throughout the exercise
APP_NAME = "MemoryDemoApp"
USER_ID = "demo_user"

# Agent with automatic memory saving
auto_memory_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="AutoMemoryAgent",
    instruction="Answer user questions.",
    tools=[preload_memory],
    after_agent_callback=auto_save_to_memory,  # Saves after each turn!, recordar : es un callback!
)

print("✅ Agent with load_memory tool created.")

# Create Session Service
session_service = InMemorySessionService()  # Handles conversations

# Create a runner for the auto-save agent
# This connects our automated agent to the session and memory services
auto_runner = Runner(
    agent=auto_memory_agent,  # Use the agent with callback + preload_memory
    app_name=APP_NAME,
    session_service=session_service,  # Same services from Section 3
    memory_service=memory_service,
)

print("✅ Runner created.")

print("✅ Agent and Runner created with memory support!")

# Test 1: Tell the agent about a gift (first conversation)
# The callback will automatically save this to memory when the turn completes

async def run_conversation_01():
    await run_session(
        auto_runner,
    "I gifted a new toy to my nephew on his 1st birthday!",
    "auto-save-test",
    )


# Test 2: Ask about the gift in a NEW session (second conversation)
# The agent should retrieve the memory using preload_memory and answer correctly

async def run_conversation_02():
    await run_session(
    auto_runner,
    "What did I gift my nephew?",
    "auto-save-test-2",  # Different session ID - proves memory works across sessions!
    )


asyncio.run(run_conversation_01()) 
asyncio.run(run_conversation_02())


## Ojo, esatmos aplicando guardado de memoria sin consolidacion!!!, el costo de la consolidacion es alto, 
# por lo que no se recomienda hacerlo en cada turno.
# Por eso es importante los Managed Memory Services, que se encargan de consolidar la memoria automaticamente y de forma eficiente