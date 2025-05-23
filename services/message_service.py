from config.supabase_client import supabase
from schemas.message import Message, MessageCreate
from postgrest.exceptions import APIError
from ai.chat_agent import get_ai_response
from ai.analyzer_agent import analyze_message

from schemas.message import Message

def create_message(chat_id: int, sender: str, content: str) -> Message | None:
    data = {
        "chat_id": chat_id,
        "sender": sender,
        "content": content
    }

    try:
        response = supabase.table("messages").insert(data).execute()
        return Message(**response.data[0]) if response.data else None
    except APIError as e:
        print("Supabase insert error:", str(e))
        return None

    
def handle_human_message(msg: MessageCreate) -> Message | None:
    human_msg = create_message(
        chat_id=msg.chat_id,
        sender="human",
        content=msg.content
    )
    if not human_msg:
        return None
    
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
    feedback_text = analyze_message(response.content, message.content)
    print("Feedback:", feedback_text)
    ai_msg = create_message(
        chat_id=msg.chat_id,
        sender="ai",
        content=response.content
    )
    return ai_msg

def get_messages(chat_id: int) -> list[Message]:
    response = supabase.table("messages") \
        .select("*") \
        .eq("chat_id", chat_id) \
        .order("timestamp") \
        .execute()
    
    raw_data = response.data or []
    return [Message(**m) for m in raw_data] 

def delete_message(message_id: int) -> bool:
    response = supabase.table("messages").delete().eq("id", message_id).execute()
    return isinstance(response.data, list) and len(response.data) > 0
