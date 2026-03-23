# Librerias Ambiente
from dotenv import load_dotenv
import os
import asyncio
# Librerias ADK
from google.adk.agents import Agent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool, FunctionTool, google_search
from google.genai import types

load_dotenv()

# API KEYS
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configuracion de retry
retry_config=types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504], # Retry on these HTTP errors
)

if retry_config:
    print("All ok!")
else:
    print("NOT OK")

# Research Agent: Su trabajo es usar la herramienta google_search y presentar los hallazgos.
research_agent = Agent(
    name="ResearchAgent",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""Eres un agente de investigación especializado. Tu único trabajo es usar la
    herramienta google_search para encontrar 2-3 piezas de información relevante sobre el tema dado y presentar los hallazgos con citas.""",
    tools=[google_search],
    output_key="research_findings",  # El resultado de este agente se almacenará en el estado de la sesión con esta clave.
)

print("✅ research_agent created.")


# Summarizer Agent : Su trabajo es tomar los hallazgos de la investigación y resumirlos en un informe claro y conciso.

summarizer_agent = Agent(
    name="SummarizerAgent",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""Read the provided research findings: {research_findings}
Create a concise summary as a bulleted list with 3-5 key points.""",
    output_key="final_summary",  # El resultado de este agente se almacenará en el estado de la sesión con esta clave.
)

print("✅ summarizer_agent created.")

# Root Coordinator : Su trabajo es coordinar a los agentes y presentar el resultado final.
root_agent = Agent(
    name="RootCoordinator",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""You are a research coordinator. Your goal is to answer the user's query by orchestrating a workflow.
1. First, you MUST call the `ResearchAgent` tool to find relevant information on the topic provided by the user.
2. Next, after receiving the research findings, you MUST call the `SummarizerAgent` tool to create a concise summary.
3. Finally, present the final summary clearly to the user as your response.""",
    output_key="final_summary",  # El resultado de este agente se almacenará en el estado de la sesión con esta clave.,
    tools=[AgentTool(agent=research_agent), AgentTool(agent=summarizer_agent)],
)

print("✅ root_agent created.")

runner = InMemoryRunner(agent=root_agent)

async def run_agent_debug():
    response = await runner.run_debug(
        "What are the latest advancements in quantum computing and what do they mean for AI?"
    )
    print(response)

asyncio.run(run_agent_debug())




