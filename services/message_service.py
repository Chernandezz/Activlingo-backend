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
    human_msg = create_message(
        chat_id=msg.chat_id,
        sender="human",
        content=msg.content
    )
    if not human_msg:
        return None
    try:
        update_word_usage(msg.user_id, msg.content)
    except Exception as e:
        print(f"⚠️ Error updating word usage: {str(e)}")

    history = get_messages(msg.chat_id)
    lc_messages = []
    for message in history:
        if message.sender == "human":
            lc_messages.append({"role": "human", "content": message.content})
        elif message.sender == "ai":
            lc_messages.append({"role": "assistant", "content": message.content})
        elif message.sender == "system":
            lc_messages.append({"role": "system", "content": message.content})

    response = get_ai_response(lc_messages)

    def analyze_and_save():
        async def async_task():
            try:
                use_multi_agent = False

                if use_multi_agent:
                    raw_feedback = await analyze_with_multiple_agents(response.content, msg.content)
                else:
                    raw_feedback = analyze_message(response.content, msg.content)

                if isinstance(raw_feedback, str):
                    feedback_data = json.loads(raw_feedback)
                elif isinstance(raw_feedback, list):
                    feedback_data = raw_feedback
                else:
                    print("⚠️ Unexpected feedback format:", type(raw_feedback))
                    return

                print("🧠 Parsed feedback:", feedback_data)
                save_analysis(human_msg.id, feedback_data)

            except Exception as e:
                print("⚠️ Could not analyze/save feedback:", e)

        asyncio.run(async_task())

    threading.Thread(target=analyze_and_save).start()

    ai_msg = create_message(
        chat_id=msg.chat_id,
        sender="ai",
        content=response.content
    )

    return ai_msg


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
