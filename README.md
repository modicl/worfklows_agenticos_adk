# Mi Primer Multiagente — Repaso con Google ADK

Repositorio de práctica para aprender a construir agentes y sistemas multiagente usando el **Google Agent Development Kit (ADK)**.
Nota: IA (Claude) usada para generación del readme y docstrings.

## Descripcion

Este repo sigue el [5-Day AI Agents Intensive](https://www.kaggle.com/learn-guide/5-day-agents) de Kaggle y Google. Cada carpeta corresponde a un día del curso y cubre un tema distinto de construcción de agentes con ADK, usando `gemini-2.5-flash-lite` como modelo base.

---

## Estructura del proyecto

### `dia_1/` — Patrones de agentes

Introducción a los tipos de agentes disponibles en ADK. Cada archivo implementa un patrón distinto de orquestación.

| Archivo | Patron | Descripcion |
|---|---|---|
| `agents.py` | **Agente coordinador** | `RootCoordinator` que orquesta un `ResearchAgent` (con `google_search`) y un `SummarizerAgent` como herramientas via `AgentTool` |
| `sequential_agents.py` | **SequentialAgent** | Pipeline de blog: `OutlineAgent` → `WriterAgent` → `EditorAgent`, cada agente pasa su output al siguiente via `output_key` |
| `parallel_agents.py` | **ParallelAgent** | Tres investigadores corriendo en paralelo (Tech, Health, Finance) seguidos de un `AggregatorAgent` que sintetiza los resultados |
| `loop_workflow_agents.py` | **LoopAgent** | _(En construccion)_ |

---

### `dia_2/` — Herramientas y ejecución de código

Agentes que usan herramientas Python personalizadas y ejecución de código con `BuiltInCodeExecutor`.

| Archivo | Descripcion |
|---|---|
| `agent.py` | Agente de conversión de moneda (`enhanced_currency_agent`) con dos herramientas de datos (`get_fee_for_payment_method`, `get_exchange_rate`) y un sub-agente `CalculationAgent` que genera y ejecuta código Python para los cálculos vía `BuiltInCodeExecutor` |
| `agente_con_herramientas.py` | Agente básico con herramientas Python personalizadas |

---

### `dia_2b/` — MCP e interoperabilidad

Integración con el **Model Context Protocol (MCP)** y operaciones de larga duración con aprobación humana.

| Carpeta | Descripcion |
|---|---|
| `agente_human_in_the_loop/` | `shipping_agent` con `ResumabilityConfig` que pausa la ejecución en pedidos grandes (>5 contenedores) y espera aprobación humana via `adk_request_confirmation`. Demuestra el flujo pause → resume con `invocation_id` |
| `agente_image_mcp/` | Agente de imágenes que se conecta al servidor MCP `@modelcontextprotocol/server-everything` via `StdioConnectionParams` para obtener imágenes usando la herramienta `getTinyImage` |
| `ejercicio/` | Ejercicio de procesamiento de imágenes en batch con MCP |

---

### `dia_3a/` — Sesiones y estado

Cómo hacer agentes con estado (stateful): desde sesiones en memoria hasta persistencia en base de datos y compactación de contexto.

| Carpeta | Descripcion |
|---|---|
| `ejemplo_sesiones/` | Chatbot básico con `InMemorySessionService`. Demuestra que el agente recuerda el nombre del usuario dentro de la misma sesión |
| `sesiones_persistentes/` | Mismo chatbot pero con `DatabaseSessionService` sobre SQLite (`my_agent_data.db`). Las sesiones sobreviven reinicios del proceso |
| `session_state/` | Agente con herramientas `save_userinfo` y `retrieve_userinfo` que leen y escriben en `tool_context.state`. Demuestra cómo las herramientas pueden persistir datos en el estado de la sesión |
| `compactacion_de_contexto/` | `App` con `EventsCompactionConfig` que compacta el historial cada 3 invocaciones (con `overlap_size=1`). Evita que el contexto crezca indefinidamente en conversaciones largas |

---

### `dia_3b/` — Memoria entre sesiones

Memoria de largo plazo que persiste información entre sesiones distintas usando `InMemoryMemoryService`.

| Archivo | Descripcion |
|---|---|
| `agent.py` | Demuestra `load_memory` vs `preload_memory`: el agente recuerda el color favorito y el cumpleaños del usuario en sesiones completamente distintas. El guardado a memoria se hace manualmente con `memory_service.add_session_to_memory()` |
| `memory_storage_automatico/agent.py` | Mismo patrón pero con `after_agent_callback` para guardar la sesión a memoria automáticamente después de cada turno, sin necesidad de llamarlo manualmente |

---

### `dia_4/` — Calidad y observabilidad

Herramientas para depurar agentes, observar su comportamiento interno y evaluar la calidad de sus respuestas.

| Carpeta | Descripcion |
|---|---|
| `research_agent/` | Agente base de búsqueda de papers científicos (`research_paper_finder_agent`) con `google_search_agent` como sub-agente y herramienta `count_papers`. Configurado para usar con `adk web` |
| `research_agent_plugins/` | Mismo agente con `LoggingPlugin` integrado. Muestra cómo observar cada evento interno del agente (llamadas al LLM, herramientas, errores) en la consola. En producción (Cloud Run), estos `print()` quedan capturados en Cloud Logging |

---

## ADK Web — Herramienta de debug local

`adk web` levanta una interfaz web local para probar agentes sin escribir código de runner. Es la principal herramienta de debug durante el desarrollo.

### Iniciar el servidor

```bash
# Desde la raíz del proyecto, apuntando a la carpeta que contiene los agentes
set -a && source .env && set +a && adk web dia_4
```

El servidor queda disponible en `http://localhost:8000`.

### Qué permite hacer

- **Chatear** con el agente directamente desde el navegador
- **Ver el trace** completo de cada invocación: qué sub-agentes se activaron, qué herramientas se llamaron y con qué argumentos, qué respondió el LLM en cada paso
- **Inspeccionar el estado de la sesión** y el historial de eventos
- **Seleccionar** entre múltiples agentes si la carpeta contiene varios

### Usar LoggingPlugin con adk web

`adk web` crea su propio runner internamente e ignora el `InMemoryRunner` definido en el código. Para activar el `LoggingPlugin` hay que pasarlo como argumento:

```bash
adk web dia_4 --extra_plugins google.adk.plugins.logging_plugin.LoggingPlugin
```

Esto imprime en la consola (en gris) cada evento interno: mensajes del usuario, inicio/fin de agentes, requests/responses al LLM, llamadas a herramientas y errores.

### Dos capas de logging

Cuando usas `adk web` verás dos tipos de logs en la consola:

| Origen | Formato de ejemplo |
|---|---|
| ADK interno (módulo `logging`) | `2026-03-30 17:03:51 - INFO - google_llm.py:185 - Sending out request...` |
| `LoggingPlugin` (print) | `[logging_plugin] 🤖 AGENT STARTING` |

El logging interno de ADK siempre está activo. El `LoggingPlugin` solo aparece si se activa con `--extra_plugins`.

En producción (Cloud Run), ambos tipos de log quedan capturados automáticamente en **Cloud Logging** sin ningún cambio en el código.

---

## Conceptos cubiertos

- `LlmAgent` / `Agent` — agente básico con instrucciones y herramientas
- `SequentialAgent` — ejecuta sub-agentes en orden pasando estado via `output_key`
- `ParallelAgent` — ejecuta sub-agentes simultáneamente
- `LoopAgent` — ejecuta un agente en ciclo hasta una condición de salida
- `AgentTool` — envuelve un agente como herramienta de otro agente
- `BuiltInCodeExecutor` — ejecuta código Python generado por el agente
- `McpToolset` — integración con servidores MCP via stdio
- `InMemorySessionService` / `DatabaseSessionService` — sesiones en RAM o SQLite
- `EventsCompactionConfig` — compactación automática del historial de eventos
- `tool_context.state` — estado de sesión accesible desde herramientas
- `InMemoryMemoryService` — memoria de largo plazo entre sesiones
- `load_memory` / `preload_memory` — herramientas para recuperar memoria
- `after_agent_callback` — callback para guardar memoria automáticamente
- `ResumabilityConfig` — operaciones pausables con aprobación humana
- `LoggingPlugin` — observabilidad de eventos en consola / Cloud Logging
- `InMemoryRunner` — runner local para pruebas y debug directo
- `HttpRetryOptions` — configuración de reintentos ante errores de API

---

## Requisitos

```bash
pip install google-adk python-dotenv
```

Necesitas una `GOOGLE_API_KEY` en un archivo `.env` en la raíz del proyecto:

```
GOOGLE_API_KEY=tu_clave_aqui
```

La puedes obtener desde [Google AI Studio](https://aistudio.google.com/).

---

## Referencia

- [Google ADK Documentation](https://google.github.io/adk-docs/)
