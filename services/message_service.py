# ---------------------------------------------
# services/message_service.py - CORREGIDO
# ---------------------------------------------

from datetime import datetime, timezone
import json
import threading
import asyncio
from uuid import UUID

# IMPORTS ACTUALIZADOS
from services.analysis_service import analyze_message_by_plan, get_system_message_from_chat, save_analysis
from ai.task_checker_agent import check_tasks_completion
from config.supabase_client import supabase
from schemas.message import Message, MessageCreate
from postgrest.exceptions import APIError
from ai.chat_agent import get_ai_response
from services.tasks_service import get_tasks_for_chat, mark_tasks_completed_bulk
from services.user_dictionary_service import update_word_usage


def create_message(chat_id: UUID, sender: str, content: str) -> Message | None:
    try:
        # 1. Insertar el nuevo mensaje
        response = supabase.table("messages").insert({
            "chat_id": str(chat_id),
            "sender": sender,
            "content": content
        }).execute()

        if not response.data:
            return None

        # 2. Actualizar el campo updated_at del chat manualmente
        supabase.table("chats").update({
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", str(chat_id)).execute()

        return Message(**response.data[0])
    
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

    # 3) Construir lista de mensajes para la IA: system primero, luego human/ai
    lc_messages = []
    for m in history:
        if m.sender == "system":
            lc_messages.append({"role": "system", "content": m.content})
    for m in history:
        if m.sender in {"human", "ai"}:
            lc_messages.append({"role": m.sender, "content": m.content})

    # 4) Obtener respuesta de la IA
    response = get_ai_response(lc_messages)

    # 5) Guardar respuesta de IA
    ai_msg = create_message(msg.chat_id, "ai", response.content)

    # 6) Verificar y marcar tareas completadas
    completed_ids = []
    try:
        tasks = get_tasks_for_chat(msg.chat_id)
        incomplete = [t for t in tasks if not t["completed"]]
        completed_ids = check_tasks_completion(msg.content, incomplete)
        if completed_ids:
            mark_tasks_completed_bulk([UUID(tid) for tid in completed_ids])
    except Exception as e:
        print("⚠️ Task checking failed:", e)

    # 7) Lanzar procesos secundarios en background
    def bg():
        process_background_tasks(msg, human_msg.id, response.content)

    threading.Thread(target=bg).start()

    # 8) Devolver la respuesta de la IA, el mensaje humano y las tareas completadas
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

    # 2) Análisis lingüístico en segundo plano - NUEVO SISTEMA
    try:
        async def analyze_async():
            try:
                print(f"🔍 Starting analysis for user {msg.user_id}")
                
                # Obtener system message del chat
                system_message = get_system_message_from_chat(msg.chat_id)
                
                # Analizar según el plan del usuario (basic o premium)
                feedback_result = await analyze_message_by_plan(
                    user_id=msg.user_id,
                    system_message=system_message,
                    ai_text=ai_response,
                    user_text=msg.content
                )
                
                # Extraer solo el feedback para guardar en BD
                feedback_data = feedback_result.get("feedback", [])
                
                if feedback_data:
                    save_analysis(human_msg_id, feedback_data)
                    print(f"✅ Saved {len(feedback_data)} analysis entries (plan: {feedback_result.get('plan_type')})")
                else:
                    print("✅ No errors found - perfect message!")
                    
            except Exception as e:
                print(f"⚠️ Analyzer error: {e}")

        asyncio.run(analyze_async())
    except Exception as e:
        print(f"⚠️ Could not launch async analysis: {e}")


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