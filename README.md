# Mi Primer Multiagente — Repaso con Google ADK

Repositorio de práctica para aprender a construir agentes y sistemas multiagente usando el **Google Agent Development Kit (ADK)**.

## Descripcion

Este repo cubre los patrones fundamentales de construccion de agentes con el ADK de Google, usando el modelo `gemini-2.5-flash-lite` como LLM base y `InMemoryRunner` para la ejecucion local. Cada archivo demuestra un tipo de workflow distinto.

## Estructura

| Archivo                   | Patron                              | Descripcion                                                                                                                         |
| ------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `agents.py`               | **Agente coordinador**              | Un `RootCoordinator` que orquesta un `ResearchAgent` (con `google_search`) y un `SummarizerAgent` como herramientas via `AgentTool` |
| `sequential_agents.py`    | **SequentialAgent**                 | Pipeline de blog: `OutlineAgent` → `WriterAgent` → `EditorAgent`, donde cada agente pasa su output al siguiente via `output_key`    |
| `parallel_agents.py`      | **ParallelAgent + SequentialAgent** | Tres investigadores corriendo en paralelo (Tech, Health, Finance) seguidos de un `AggregatorAgent` que sintetiza los resultados     |
| `loop_workflow_agents.py` | **LoopAgent**                       | _(En construccion)_                                                                                                                 |

## Curso: 5-Day AI Agents Intensive con Google

Este repositorio sigue el programa del [5-Day AI Agents Intensive](https://www.kaggle.com/learn-guide/5-day-agents) de Kaggle y Google. Cada dia corresponde a un modulo del curso:

### Dia 1 — Introduction to Agents
Conceptos fundacionales de los agentes de IA: como se definen, en que se diferencian de una aplicacion LLM tradicional, y las arquitecturas agénticas. Se construye el primer agente con ADK y el primer sistema multiagente.

**Archivos:** `agents.py`

### Dia 2 — Agent Tools & Interoperability with MCP
Herramientas externas que permiten al agente tomar acciones: funciones Python, APIs, y el Model Context Protocol (MCP). Tambien cubre operaciones de larga duracion con aprobacion humana (human-in-the-loop).

**Archivos:** *(pendiente)*

### Dia 3 — Context Engineering: Sessions & Memory
Como hacer agentes con estado (stateful): manejo del historial de conversacion, memoria de corto plazo dentro de una sesion y memoria de largo plazo que persiste entre sesiones.

**Archivos:** *(pendiente)*

### Dia 4 — Agent Quality
Observabilidad, logs, trazas y metricas para depurar agentes. Estrategias de evaluacion: LLM-as-a-Judge y Human-in-the-Loop (HITL) para medir y mejorar la calidad de respuestas y uso de herramientas.

**Archivos:** *(pendiente)*

### Dia 5 — Prototype to Production
Despliegue y escalado de agentes a produccion. Protocolo Agent2Agent (A2A) para sistemas multiagente distribuidos. Despliegue en Vertex AI Agent Engine en Google Cloud.

**Archivos:** *(pendiente)*

---

## Conceptos cubiertos

- `Agent` — agente basico con instrucciones y herramientas
- `SequentialAgent` — ejecuta sub-agentes en orden, pasando estado entre ellos
- `ParallelAgent` — ejecuta sub-agentes de forma simultanea
- `LoopAgent` — ejecuta un agente en ciclo hasta una condicion de salida
- `AgentTool` — envuelve un agente como herramienta de otro agente
- `output_key` — mecanismo para compartir estado entre agentes del pipeline
- `InMemoryRunner` — runner local para pruebas y debug
- Configuracion de reintentos con `HttpRetryOptions`

## Requisitos

```bash
pip install google-adk python-dotenv
```

Necesitas una `GOOGLE_API_KEY` en un archivo `.env`:
Lo puedes obtener de Google AI Studio

```
GOOGLE_API_KEY=tu_clave_aqui
```

## Ejecucion

```bash
# Agente coordinador con herramientas
python agents.py

# Pipeline secuencial
python sequential_agents.py

# Investigacion paralela
python parallel_agents.py
```

## Referencia

- [Google ADK Documentation](https://google.github.io/adk-docs/)
