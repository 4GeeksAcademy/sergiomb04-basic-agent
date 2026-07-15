import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent
CONVERSATION_LOG_FILE = BASE_DIR / "conversation_log.csv"
LOG_HEADERS = ["actor", "message", "tool_call", "timestamp"]


def now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def ensure_conversation_log_exists() -> None:
	if not CONVERSATION_LOG_FILE.exists() or CONVERSATION_LOG_FILE.stat().st_size == 0:
		with CONVERSATION_LOG_FILE.open("w", newline="", encoding="utf-8") as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=LOG_HEADERS)
			writer.writeheader()


def log_event(actor: str, message: str, tool_call: str = "") -> None:
	ensure_conversation_log_exists()
	with CONVERSATION_LOG_FILE.open("a", newline="", encoding="utf-8") as csv_file:
		writer = csv.DictWriter(csv_file, fieldnames=LOG_HEADERS)
		writer.writerow(
			{
				"actor": actor,
				"message": message,
				"tool_call": tool_call,
				"timestamp": now_iso(),
			}
		)


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

client: OpenAI | None = None


def get_llm_client() -> OpenAI:
	global client
	if client is not None:
		return client
	if not GROQ_API_KEY:
		raise RuntimeError("Missing GROQ_API_KEY in .env")
	client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
	return client

messages: List[Dict[str, Any]] = [
	{
		"role": "system",
		"content": (
			"Eres un asistente para inventario. Usa herramientas cuando sea necesario "
			"y responde de forma clara en espanol."
		),
	}
]

TOOLS = [
	{
		"type": "function",
		"function": {
			"name": "get_inventory",
			"description": "Obtiene todos los productos del inventario.",
			"parameters": {
				"type": "object",
				"properties": {},
				"additionalProperties": False,
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "create_product",
			"description": "Crea un producto en inventario con nombre, cantidad y unidad.",
			"parameters": {
				"type": "object",
				"properties": {
					"name": {"type": "string", "description": "Nombre del producto."},
					"quantity": {
						"type": "integer",
						"description": "Cantidad inicial del producto.",
					},
					"unit": {"type": "string", "description": "Unidad del producto."},
				},
				"required": ["name", "quantity", "unit"],
				"additionalProperties": False,
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "update_stock",
			"description": "Ajusta el stock de un producto por ID usando un delta.",
			"parameters": {
				"type": "object",
				"properties": {
					"product_id": {
						"type": "integer",
						"description": "ID del producto a actualizar.",
					},
					"delta": {
						"type": "integer",
						"description": "Cambio en stock, positivo o negativo.",
					},
				},
				"required": ["product_id", "delta"],
				"additionalProperties": False,
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "get_inventory_alerts",
			"description": "Lista productos con cantidad menor a un umbral.",
			"parameters": {
				"type": "object",
				"properties": {
					"threshold": {
						"type": "integer",
						"description": "Umbral minimo opcional (default 10).",
					}
				},
				"additionalProperties": False,
			},
		},
	},
]


def _handle_http_error(error: requests.HTTPError) -> Dict[str, Any]:
	status_code = error.response.status_code if error.response is not None else 500
	text = error.response.text if error.response is not None else str(error)
	return {"error": f"HTTP {status_code}", "detail": text}


def api_get_inventory() -> Dict[str, Any]:
	try:
		response = requests.get(f"{API_BASE_URL}/inventory", timeout=10)
		response.raise_for_status()
		return response.json()
	except requests.HTTPError as error:
		return _handle_http_error(error)
	except requests.RequestException as error:
		return {"error": "Request failed", "detail": str(error)}


def api_create_product(name: str, quantity: int, unit: str) -> Dict[str, Any]:
	payload = {"name": name, "quantity": quantity, "unit": unit}
	try:
		response = requests.post(f"{API_BASE_URL}/inventory", json=payload, timeout=10)
		response.raise_for_status()
		return response.json()
	except requests.HTTPError as error:
		return _handle_http_error(error)
	except requests.RequestException as error:
		return {"error": "Request failed", "detail": str(error)}


def api_update_stock(product_id: int, delta: int) -> Dict[str, Any]:
	payload = {"delta": delta}
	try:
		response = requests.patch(
			f"{API_BASE_URL}/inventory/{product_id}", json=payload, timeout=10
		)
		response.raise_for_status()
		return response.json()
	except requests.HTTPError as error:
		return _handle_http_error(error)
	except requests.RequestException as error:
		return {"error": "Request failed", "detail": str(error)}


def api_get_alerts(threshold: int | None = None) -> Dict[str, Any]:
	params: Dict[str, Any] = {}
	if threshold is not None:
		params["threshold"] = threshold
	try:
		response = requests.get(f"{API_BASE_URL}/inventory/alerts", params=params, timeout=10)
		response.raise_for_status()
		return response.json()
	except requests.HTTPError as error:
		return _handle_http_error(error)
	except requests.RequestException as error:
		return {"error": "Request failed", "detail": str(error)}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
	if tool_name == "get_inventory":
		return api_get_inventory()
	if tool_name == "create_product":
		return api_create_product(
			name=arguments["name"],
			quantity=arguments["quantity"],
			unit=arguments["unit"],
		)
	if tool_name == "update_stock":
		return api_update_stock(
			product_id=arguments["product_id"],
			delta=arguments["delta"],
		)
	if tool_name == "get_inventory_alerts":
		return api_get_alerts(threshold=arguments.get("threshold"))
	return {"error": f"Unknown tool: {tool_name}"}


def run_agent_loop(user_input: str) -> str:
	llm_client = get_llm_client()
	messages.append({"role": "user", "content": user_input})
	log_event(actor="user", message=user_input)

	while True:
		completion = llm_client.chat.completions.create(
			model=MODEL_NAME,
			messages=messages,
			tools=TOOLS,
			tool_choice="auto",
		)
		assistant_message = completion.choices[0].message

		assistant_content = assistant_message.content or ""
		tool_calls = assistant_message.tool_calls or []

		assistant_message_payload: Dict[str, Any] = {
			"role": "assistant",
			"content": assistant_content,
		}
		if tool_calls:
			assistant_message_payload["tool_calls"] = [
				{
					"id": call.id,
					"type": "function",
					"function": {
						"name": call.function.name,
						"arguments": call.function.arguments,
					},
				}
				for call in tool_calls
			]
		messages.append(assistant_message_payload)

		if not tool_calls:
			final_text = assistant_content.strip() or "No tengo una respuesta en este momento."
			log_event(actor="assistant", message=final_text)
			return final_text

		for tool_call in tool_calls:
			tool_name = tool_call.function.name
			try:
				args = json.loads(tool_call.function.arguments or "{}")
			except json.JSONDecodeError:
				args = {}

			log_event(actor="tool", message=json.dumps(args, ensure_ascii=True), tool_call=tool_name)
			result = execute_tool(tool_name=tool_name, arguments=args)
			result_json = json.dumps(result, ensure_ascii=True)
			log_event(actor="tool", message=result_json, tool_call=tool_name)

			messages.append(
				{
					"role": "tool",
					"tool_call_id": tool_call.id,
					"name": tool_name,
					"content": result_json,
				}
			)


def run_cli() -> None:
	if not GROQ_API_KEY:
		print("Falta GROQ_API_KEY en .env. Configuralo antes de ejecutar el agente.")
		return
	print("Agente de inventario listo. Escribe 'exit' o 'quit' para salir.")
	while True:
		user_input = input("Tu mensaje: ").strip()
		if user_input.lower() in {"exit", "quit"}:
			print("Hasta luego.")
			break
		if not user_input:
			continue
		answer = run_agent_loop(user_input)
		print(f"Agente: {answer}")


if __name__ == "__main__":
	run_cli()
