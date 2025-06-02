import json
import threading
import asyncio
from uuid import UUID

from ai.multi_agent_analyzer import analyze_with_multiple_agents
from ai.analyzer_agent import analyze_message
from config.supabase_client import supabase
from schemas.message import Message, MessageCreate
from postgrest.exceptions import APIError
from ai.chat_agent import get_ai_response
from services.analysis_service import save_analysis
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


def handle_human_message(msg: MessageCreate) -> Message | None:
    # 1. Guardar mensaje humano
    human_msg = create_message(msg.chat_id, "human", msg.content)
    if not human_msg:
        return None

    # 2. Obtener historial y respuesta IA
    history = get_messages(msg.chat_id)
    lc_messages = [{"role": m.sender, "content": m.content} for m in history if m.sender in {"human", "ai", "system"}]

    response = get_ai_response(lc_messages)

    # 3. Guardar mensaje de la IA
    ai_msg = create_message(msg.chat_id, "ai", response.content)

    # 4. Lanzar procesamiento pesado en segundo plano
    threading.Thread(target=process_background_tasks, args=(msg, human_msg.id, response.content)).start()

    # 5. Retornar respuesta al frontend lo antes posible
    return ai_msg


def process_background_tasks(msg: MessageCreate, human_msg_id: UUID, ai_response: str):
    # Palabras: actualizar uso y crear nuevas
    try:
        update_word_usage(msg.user_id, msg.content)
    except Exception as e:
        print("⚠️ Word update failed:", e)

    # Análisis lingüístico
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
