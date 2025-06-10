# ---------------------------------------------
# services/message_service.py
# ---------------------------------------------

import json
import threading
import asyncio
from uuid import UUID

from ai.multi_agent_analyzer import analyze_with_multiple_agents
from ai.analyzer_agent import analyze_message
from ai.task_checker_agent import check_tasks_completion
from config.supabase_client import supabase
from schemas.message import Message, MessageCreate
from postgrest.exceptions import APIError
from ai.chat_agent import get_ai_response
from services.analysis_service import save_analysis
from services.tasks_service import get_tasks_for_chat, mark_tasks_completed_bulk
from services.user_dictionary_service import update_word_usage


def create_message(chat_id: UUID, sender: str, content: str) -> Message | None:
    try:
        response = supabase.table("messages").insert({
            "chat_id": str(chat_id),
            "sender": sender,
            "content": content
        }).execute()
        return Message(**response.data[0]) if response.data else None
    except APIError as e:
        print("⚠️ Supabase insert error:", str(e))
        return None


def handle_human_message(msg: MessageCreate) -> dict:
    # 1) Guardar mensaje humano
    human_msg = create_message(msg.chat_id, "human", msg.content)
    if not human_msg:
        return {"error": "Could not save message"}

    # 2) Obtener todo el historial (incluye system, human, ai)
    history = get_messages(msg.chat_id)

    # 3) Asegurar que exista un mensaje 'system' en la base de datos
    #    En create_chat ya se insertó un 'system' inicial.
    #    Aquí no lo re-creamos, simplemente lo usamos si está.
    #    Si por algún motivo no hay 'system', se asume que no se perdió
    #    porque create_chat lo agrega siempre al crear el chat.

    # 4) Construir lista de mensajes para la IA: system primero, luego human/ai
    lc_messages = []
    for m in history:
        if m.sender == "system":
            lc_messages.append({"role": "system", "content": m.content})
    for m in history:
        if m.sender in {"human", "ai"}:
            lc_messages.append({"role": m.sender, "content": m.content})

    # 5) Obtener respuesta de la IA
    response = get_ai_response(lc_messages)

    # 6) Guardar respuesta de IA
    ai_msg = create_message(msg.chat_id, "ai", response.content)

    # 7) Verificar y marcar tareas completadas
    completed_ids = []
    try:
        tasks = get_tasks_for_chat(msg.chat_id)
        incomplete = [t for t in tasks if not t["completed"]]
        completed_ids = check_tasks_completion(msg.content, incomplete)
        if completed_ids:
            mark_tasks_completed_bulk([UUID(tid) for tid in completed_ids])
    except Exception as e:
        print("⚠️ Task checking failed:", e)

    # 8) Lanzar procesos secundarios en background
    def bg():
        process_background_tasks(msg, human_msg.id, response.content)

    threading.Thread(target=bg).start()

    # 9) Devolver la respuesta de la IA, el mensaje humano y las tareas completadas
    return {
        "message": ai_msg,
        "human_message": human_msg,
        "completed_tasks": [str(tid) for tid in completed_ids]
    }


def process_background_tasks(msg: MessageCreate, human_msg_id: UUID, ai_response: str):
    # 1) Actualizar uso de palabras en el diccionario
    try:
        update_word_usage(msg.user_id, msg.content)
    except Exception as e:
        print("⚠️ Word update failed:", e)

    # 2) Análisis lingüístico en segundo plano
    try:
        async def analyze_async():
            try:
                feedback = analyze_message(ai_response, msg.content)
                feedback_data = json.loads(feedback) if isinstance(feedback, str) else feedback
                save_analysis(human_msg_id, feedback_data)
            except Exception as e:
                print("⚠️ Analyzer error:", e)

        asyncio.run(analyze_async())
    except Exception as e:
        print("⚠️ Could not launch async analysis:", e)


def get_messages(chat_id: UUID) -> list[Message]:
    response = (
        supabase
        .table("messages")
        .select("*")
        .eq("chat_id", str(chat_id))
        .order("timestamp")
        .execute()
    )
    raw_data = response.data or []
    return [Message(**m) for m in raw_data]


def delete_message(message_id: UUID) -> bool:
    response = (
        supabase
        .table("messages")
        .delete()
        .eq("id", str(message_id))
        .execute()
    )
    return isinstance(response.data, list) and len(response.data) > 0
