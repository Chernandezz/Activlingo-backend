from ai.chat_tasks import generate_tasks
from config.supabase_client import supabase
from schemas.chat import Chat
from schemas.chat_create import ChatCreate
from postgrest.exceptions import APIError
from ai.chat_agent import generate_system_message, get_ai_response
from services.message_service import create_message
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from uuid import UUID

from services.tasks_service import get_tasks_for_chat


def create_chat(user_id: UUID, chat_data: ChatCreate) -> dict | None:
    data = chat_data.model_dump()
    data["user_id"] = str(user_id)

    try:
        response = supabase.table("chats").insert(data).execute()
        chat = response.data[0] if response.data else None

        if chat:
            system_msg = generate_system_message(chat["role"], chat["context"])
            create_message(chat_id=UUID(chat["id"]), sender="system", content=system_msg)
            bot_response = get_ai_response([SystemMessage(content=system_msg)])
            
            create_message(chat_id=UUID(chat["id"]), sender="ai", content=bot_response.content)
            chat["initial_message"] = bot_response.content

            # 🧠 Insertar tareas con completed: False
            tasks = generate_tasks(chat["role"], chat["context"])
            for task in tasks:
                supabase.table("chat_missions").insert({
                    "chat_id": chat["id"],
                    "description": task,
                    "completed": False,
                }).execute()

        # 🔄 Obtener tareas completas desde la DB
        task_objs = get_tasks_for_chat(UUID(chat["id"]))
        chat["tasks"] = task_objs  # Ya incluye description y completed

        return chat
    except APIError as e:
        if "23503" in str(e):
            return None
        raise e


def get_chats(user_id: UUID) -> list[Chat]:
    response = (
        supabase
        .table("chats")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def get_chat_by_id(chat_id: UUID) -> dict | None:
    response = (
        supabase
        .table("chats")
        .select("*")
        .eq("id", str(chat_id))
        .limit(1)
        .execute()
    )
    chat = response.data[0] if response.data else None
    if not chat:
        return None

    # 🧠 Obtener tareas completas
    tasks = get_tasks_for_chat(chat_id)
    chat["tasks"] = tasks

    return chat


def delete_chat(chat_id: UUID) -> bool:
    response = supabase.table("chats").delete().eq("id", str(chat_id)).execute()
    return bool(response.data)
