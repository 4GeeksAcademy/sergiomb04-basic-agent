# Inventario con FastAPI + Agente IA (sin frameworks de agentes)

Proyecto compuesto por:

- API REST con FastAPI para gestionar inventario persistido en CSV.
- Agente en Python con loop manual de tools (sin LangChain, sin LlamaIndex, sin AutoGen).

## Estructura

```text
api/
	app.py
agent.py
products.csv
conversation_log.csv
.env.example
.gitignore
README.md
```

## Requisitos

- Python 3.10+
- Dependencias:

```bash
pip install fastapi uvicorn requests python-dotenv openai
```

## Configuracion

1. Copia `.env.example` a `.env`.
2. Completa `GROQ_API_KEY`.

Variables esperadas:

- `GROQ_API_KEY`
- `GROQ_MODEL` (por defecto `llama-3.1-70b-versatile`)
- `GROQ_BASE_URL` (por defecto `https://api.groq.com/openai/v1`)
- `API_BASE_URL` (por defecto `http://127.0.0.1:8000`)

## Ejecutar en dos terminales

### Terminal 1: API

```bash
uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2: Agente

```bash
python agent.py
```

Comandos de salida del CLI:

- `exit`
- `quit`

## Endpoints de la API

- `GET /inventory`
- `POST /inventory`
- `PATCH /inventory/{product_id}`
- `GET /inventory/alerts?threshold=10`

## Persistencia y logging

- `products.csv` guarda el inventario y conserva datos tras reiniciar la API.
- `conversation_log.csv` es append-only y registra:
	- actor (`user`, `assistant`, `tool`)
	- message
	- tool_call
	- timestamp (ISO 8601)
