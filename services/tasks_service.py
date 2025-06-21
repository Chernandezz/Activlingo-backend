from typing import List
from config.supabase_client import supabase
from uuid import UUID

def get_tasks_for_chat(chat_id: UUID) -> list[dict]:
    response = (
        supabase
        .table("chat_missions")
        .select("id, description, completed, chat_id, created_at")
        .eq("chat_id", str(chat_id))
        .execute()
    )
    return response.data or []


def mark_tasks_completed_bulk(task_ids: List[UUID]) -> List[UUID]:
    response = (
        supabase
        .table("chat_missions")
        .update({"completed": True, "completed_at": "now()"})
        .in_("id", [str(tid) for tid in task_ids])
        .execute()
    )
    return [UUID(t["id"]) for t in response.data or []]

