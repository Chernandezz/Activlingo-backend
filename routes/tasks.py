from fastapi import APIRouter
from uuid import UUID
from typing import List
from schemas.tasks import Task
from services.tasks_service import get_tasks_for_chat, mark_tasks_completed_bulk

tasks_router = APIRouter()

@tasks_router.get("/{chat_id}", response_model=List[Task])
def get_tasks(chat_id: UUID):
    return get_tasks_for_chat(chat_id)

@tasks_router.post("/complete")
def complete_tasks(task_ids: List[UUID]):
    completed = mark_tasks_completed_bulk(task_ids)
    return {"completed_tasks": completed}
