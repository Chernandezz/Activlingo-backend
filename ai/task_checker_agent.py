import json
from uuid import UUID
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

task_checker = ChatOpenAI(model="gpt-4o", temperature=0)

def check_tasks_completion(message: str, tasks: list[dict]) -> list[UUID]:
    """
    Revisa cuáles tareas fueron completadas según el mensaje del usuario.
    Recibe una lista de dicts con keys: id, description.
    Devuelve lista de UUIDs completados.
    """
    task_descriptions = "\n".join(
        [f"{i+1}. {t['description']} (id: {t['id']})" for i, t in enumerate(tasks)]
    )

    system = SystemMessage(content="""
You are a smart evaluator for English learning tasks.
Given a user's message and a list of tasks, return the IDs of the tasks that are clearly completed.
Only return the task IDs — no explanation, no extra words.

Rules:
- Match intent, not exact wording.
- If the user fulfills the action or expression, consider it completed.
- IDs must match exactly as provided.
- Output format: ["uuid1", "uuid2"]
""")

    user = HumanMessage(content=f"""
User message:
"{message}"

Tasks:
{task_descriptions}

Which tasks are completed? Reply ONLY with a JSON list of task IDs.
""")

    try:
        response = task_checker.invoke([system, user])
        return json.loads(response.content)
    except Exception as e:
        print("❌ Multi-task check failed:", e)
        return []
