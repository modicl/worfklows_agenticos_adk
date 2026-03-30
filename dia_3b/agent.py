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

# Create agent
user_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="MemoryDemoAgent",
    instruction="Answer user questions in simple words. Use load_memory tool if you need to recall past conversations.",
    tools=[
        preload_memory
    ],  # Agent now has access to Memory and can search it whenever it decides to!
)

print("✅ Agent with load_memory tool created.")

# Create Session Service
session_service = InMemorySessionService()  # Handles conversations

# Create runner with BOTH services
runner = Runner(
    agent=user_agent,
    app_name="MemoryDemoApp",
    session_service=session_service,
    memory_service=memory_service,  # Memory service is now available!
)

print("✅ Agent and Runner created with memory support!")

# User tells agent about their favorite color

async def run_conversation_01():
    await run_session(
        runner,
        "My favorite color is blue-green. Can you write a Haiku about it?",
        "conversation-01",  # Session ID
    )
    session = await session_service.get_session(
    app_name=APP_NAME, user_id=USER_ID, session_id="conversation-01"
)

    # Let's see what's in the session
    print("📝 Session contains:")
    for event in session.events:
        text = (
            event.content.parts[0].text[:60]
            if event.content and event.content.parts
            else "(empty)"
        )
        print(f"  {event.content.role}: {text}...")
    # This is the key method!
    await memory_service.add_session_to_memory(session)

    print("✅ Session added to memory!")

async def run_conversation_02():
    await run_session(
        runner,
        "What is my favorite color?",
        "conversation-02",  # Session ID
    )

async def run_conversation_03():
    await run_session(
        runner,
        "My birthday is on October 30th.",
        "birthday-session-01",  # Session ID
    )
    # Gurdamos manualmente los datos de la session
    birthday_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="birthday-session-01"
    )
    # Gurdamos la session a la memoria manualmente
    await memory_service.add_session_to_memory(birthday_session)

    print("✅ Birthday session saved to memory!")

async def run_conversation_04():
    await run_session(
        runner,
        "When is my birthday?",
        "birthday-session-02",  # Sesion totalmente distinta, deberia de saber mi cumpleaños!
    )

asyncio.run(run_conversation_01()) # Le digo que me gusta blue-green
asyncio.run(run_conversation_02()) # Preguntamos por el color en memoria
asyncio.run(run_conversation_03()) # La del cumpleaños
asyncio.run(run_conversation_04()) # Preguntamos por el cumpleaños en memoria

# Nota mia: No es necesario guardar la session a la memoria manualmente, se puede hacer automaticamente con el runner.
# Nota mia 2: Al darle el load_memory al agente, este puede buscar en la memoria y recuperar la informacion que necesita, pero 
# En uno de los casos no lo hizo, no se porque! Quizas por el prompt que le di?
# Si usase preload_memory si o si llama, pero es menos eficiente!

# Debugeando la memoria de la sesion
# Search for color preferences
async def debug_memory():
    search_response = await memory_service.search_memory(
        app_name=APP_NAME, user_id=USER_ID, query="Is the user borned in October 30th ?"
    )

    print("🔍 Search Results:")
    print(f"  Found {len(search_response.memories)} relevant memories")
    print()

    for memory in search_response.memories:
        if memory.content and memory.content.parts:
            text = memory.content.parts[0].text[:80]
        print(f"  [{memory.author}]: {text}...")

asyncio.run(debug_memory())

# Recordar que como estamos usando la memoria en la RAM la busqueda no es semantica si no que exacta, por eso las memorias
# no se recuperan si no se usa la palabra exacta y podemos ver que guarda literalmente la sesion!