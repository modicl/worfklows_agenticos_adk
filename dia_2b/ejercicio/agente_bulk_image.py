import os
from dotenv import load_dotenv

load_dotenv()

# Configurar Vertex AI via variables de entorno (requerido antes de importar ADK)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID", ""))
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

import asyncio
import uuid
import base64

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# Umbral para requerir confirmación humana
BULK_IMAGE_TRESHOLD = 2

# Carpeta donde se guardan las imágenes procesadas (misma que este archivo)
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# MCP Toolset
# ---------------------------------------------------------------------------
mcp_image_server = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-everything"],
            tool_filter=["get-tiny-image"],  # nombre real del tool MCP
        ),
        timeout=30,
    )
)

# ---------------------------------------------------------------------------
# Tool con lógica HITL
# Recibe la CANTIDAD de imágenes a procesar (no la lista, que aún no existe)
# ---------------------------------------------------------------------------
def process_images(count: int, tool_context: ToolContext) -> dict:
    """Controla cuántas imágenes procesar con get-tiny-image.
    - 1 imagen  → procede de inmediato.
    - 2 o más   → requiere confirmación humana.
    """

    # SCENARIO 1: imagen única → proceder de inmediato
    if count < BULK_IMAGE_TRESHOLD:
        return {
            "status": "proceed",
            "count": count,
            "message": f"Procesando {count} imagen de inmediato.",
        }

    # SCENARIO 2: bulk, primera llamada → PAUSA
    if not tool_context.tool_confirmation:
        tool_context.request_confirmation(
            hint=f"⚠️ Procesamiento bulk: {count} imágenes. ¿Confirmar?",
            payload={"count": count},
        )
        return {
            "status": "pending",
            "message": f"Se requiere confirmación humana para procesar {count} imágenes.",
        }

    # SCENARIO 3: retomando tras decisión humana
    if tool_context.tool_confirmation.confirmed:
        return {
            "status": "proceed",
            "count": count,
            "message": f"Bulk aprobado: {count} imágenes.",
        }
    else:
        return {
            "status": "rejected",
            "message": f"Bulk rechazado: {count} imágenes.",
        }

# ---------------------------------------------------------------------------
# Agente + App
# ---------------------------------------------------------------------------
bulk_image_agent = LlmAgent(
    name="bulk_image_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""
    Eres un agente experto en procesamiento de imágenes.

    PASOS OBLIGATORIOS (en este orden):
    1. Llama a process_images con el número de imágenes que el usuario quiere.
    2. Si el status es "proceed":
       - Llama a get-tiny-image exactamente <count> veces.
       - Nada más. El sistema guarda las imágenes automáticamente.
    3. Si el status es "pending", informa que se requiere aprobación humana.
    4. Si el status es "rejected", informa que fue cancelado.
    5. Responde con un resumen: cuántas imágenes se obtuvieron.
    """,
    tools=[FunctionTool(process_images), mcp_image_server],
)

bulk_image_app = App(
    name="bulk_image_coordinator",
    root_agent=bulk_image_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

session_service = InMemorySessionService()

bulk_image_runner = Runner(
    app=bulk_image_app,
    session_service=session_service,
)

# ---------------------------------------------------------------------------
# Helpers HITL
# ---------------------------------------------------------------------------
def check_for_approval(events):
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_confirmation"
                ):
                    return {
                        "approval_id": part.function_call.id,
                        "invocation_id": event.invocation_id,
                    }
    return None


def create_approval_response(approval_info, approved):
    confirmation_response = types.FunctionResponse(
        id=approval_info["approval_id"],
        name="adk_request_confirmation",
        response={"confirmed": approved},
    )
    return types.Content(
        role="user", parts=[types.Part(function_response=confirmation_response)]
    )


def print_agent_response(events):
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Agent > {part.text}")


# ---------------------------------------------------------------------------
# Guardar imágenes interceptando inline_data de los eventos
# get-tiny-image devuelve bytes como inline_data, NO como string base64.
# El agente ve la imagen visualmente pero no puede extraer el base64 como texto,
# así que guardamos directamente desde los eventos en Python.
# ---------------------------------------------------------------------------

def save_images_from_events(events, prefix="muestra"):
    """Guarda imágenes desde respuestas get-tiny-image.

    ADK empaqueta la respuesta MCP en:
      part.function_response.response = {
          'content': [
              {'type': 'text', 'text': '...'},
              {'type': 'image', 'data': '<base64>'},
          ]
      }
    """
    saved = []
    idx = 1
    for event in events:
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            if not (part.function_response and part.function_response.name == "get-tiny-image"):
                continue
            content_items = part.function_response.response.get("content", [])
            for item in content_items:
                if item.get("type") == "image" and item.get("data"):
                    filename = f"{prefix}_{idx}.png"
                    output_path = os.path.join(AGENT_DIR, filename)
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(item["data"]))
                    print(f"💾 Guardada: {output_path}")
                    saved.append(output_path)
                    idx += 1
    return saved


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
async def run_bulk_image_workflow(query: str, auto_approve: bool = True):
    print(f"\n{'='*60}")
    print(f"User > {query}\n")

    session_id = f"images_{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name="bulk_image_coordinator", user_id="test_user", session_id=session_id
    )

    query_content = types.Content(role="user", parts=[types.Part(text=query)])
    events = []

    # STEP 1: enviar solicitud al agente
    async for event in bulk_image_runner.run_async(
        user_id="test_user", session_id=session_id, new_message=query_content
    ):
        events.append(event)

    # STEP 2: guardar imágenes del primer run (caso imagen única)
    save_images_from_events(events)

    # STEP 3: escanear si hay pausa por confirmación bulk
    approval_info = check_for_approval(events)

    if approval_info:
        # PATH A: bulk → esperar decisión humana
        print(f"⏸️  Pausado: se requiere aprobación bulk...")
        print(f"🤔 Decisión humana: {'APROBAR ✅' if auto_approve else 'RECHAZAR ❌'}\n")

        resume_events = []
        async for event in bulk_image_runner.run_async(
            user_id="test_user",
            session_id=session_id,
            new_message=create_approval_response(approval_info, auto_approve),
            invocation_id=approval_info["invocation_id"],
        ):
            resume_events.append(event)
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent > {part.text}")

        # Guardar imágenes del run de reanudación
        save_images_from_events(resume_events)
    else:
        # PATH B: imagen única → ya terminó
        print_agent_response(events)

    print(f"{'='*60}\n")


async def main():
    # Demo 1: 1 imagen → inmediato, sin confirmación
    await run_bulk_image_workflow("Obtén 1 imagen pequeña de muestra.")

    # Demo 2: bulk → aprobado
    await run_bulk_image_workflow(
        "Obtén 3 imágenes pequeñas de muestra.",
        auto_approve=True,
    )

    # Demo 3: bulk → rechazado
    await run_bulk_image_workflow(
        "Obtén 3 imágenes pequeñas de muestra.",
        auto_approve=False,
    )


if __name__ == "__main__":
    asyncio.run(main())
