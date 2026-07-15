# Inventario con FastAPI y Agente IA

Aplicacion de inventario con dos piezas:

- Una API REST en FastAPI que guarda productos en un CSV.
- Un agente en Python que usa un modelo compatible con OpenAI (Groq) y decide que endpoint llamar mediante tools.

No usa frameworks de agentes (LangChain, LlamaIndex, AutoGen).

## Que hace la aplicacion hoy

1. Lista inventario completo.
2. Crea productos nuevos con ID automatico.
3. Ajusta stock por delta positivo o negativo.
4. Consulta alertas por umbral de stock bajo.
5. Persiste datos en products.csv aunque reinicies la API.
6. Registra la conversacion del agente en conversation_log.csv en modo append-only.

## Estructura principal

```text
api/
  app.py
agent.py
products.csv
conversation_log.csv
.env.example
.gitignore
README.md
README.es.md
```

## Requisitos

- Python 3.10 o superior
- Dependencias:

```bash
pip install fastapi uvicorn requests python-dotenv openai
```

## Configuracion

1. Copia .env.example a .env.
2. Completa al menos GROQ_API_KEY.

Variables soportadas:

- GROQ_API_KEY
- GROQ_MODEL (default: llama-3.1-70b-versatile)
- GROQ_BASE_URL (default: https://api.groq.com/openai/v1)
- API_BASE_URL (default: http://127.0.0.1:8000)

## Como ejecutar (2 terminales)

Terminal 1: API

```bash
uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2: agente

```bash
python agent.py
```

Para salir del agente:

- exit
- quit

## Como hacer que el agente haga cosas

Escribe peticiones claras en lenguaje natural. El agente decide automaticamente que tool usar.

Ejemplos efectivos:

1. Listar inventario

```text
Muestrame todo el inventario actual.
```

2. Crear producto

```text
Crea un producto llamado leche con 12 unidades de litro.
```

3. Subir stock

```text
Suma 8 unidades al producto con id 1.
```

4. Bajar stock

```text
Resta 3 unidades al producto con id 1.
```

5. Ver alertas con umbral por defecto (10)

```text
Que productos estan en alerta de stock bajo?
```

6. Ver alertas con umbral personalizado

```text
Dame alertas de inventario por debajo de 20.
```

## Endpoints disponibles

- GET /inventory
- POST /inventory
- PATCH /inventory/{product_id}
- GET /inventory/alerts?threshold=10

## Validaciones y codigos HTTP

- POST /inventory valida nombre, unidad y cantidad no negativa.
- PATCH /inventory/{product_id} devuelve:
  - 404 si el producto no existe.
  - 400 si el delta deja la cantidad en negativo.
- Errores de validacion de payload devuelven 422.

## Persistencia y trazabilidad

- products.csv guarda el inventario y se mantiene entre reinicios.
- conversation_log.csv registra cada evento:
  - user: mensaje del usuario.
  - assistant: respuesta final del agente.
  - tool: llamada y resultado de cada herramienta.
- Campos del log:
  - actor
  - message
  - tool_call
  - timestamp (ISO 8601)

## Limites actuales

- El agente depende de que la API este levantada.
- Si falta GROQ_API_KEY, el agente no inicia.
- El inventario usa CSV simple (sin concurrencia avanzada ni base de datos).
