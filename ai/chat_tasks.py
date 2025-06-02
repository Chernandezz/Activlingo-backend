from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

tasks_agent = ChatOpenAI(
    model="gpt-4o"
)

def generate_tasks(role: str, context: str) -> list[dict]:
    system_prompt = SystemMessage(content="""
You are a language tutor that creates simple, friendly conversation tasks to help learners practice English in a simulated chat.

🧠 Context:
- The student is chatting with an AI pretending to be a **{role}**.
- The situation/context is: "{context}"
- The student will try to complete small tasks during the chat to practice real English.

🎯 Your task:
Generate 4 short and concrete task for the **student**. Each task should:
- Be a short instruction like: “Ask the {role}...” or “Tell the {role}...”
- Include a clear language goal: use of a word, tense, idiom, polite phrase, structure, etc.
- Be simple (A2–B1 level) and something the student can do in 1–2 sentences.
- ✅ Also include a natural English example the student could say.
- 🧠 Write the example directly after the instruction like this
- Write the tasks in spanish, but the examples should be in English.
  "Preguntale a la mesera sobre el menu de una manera educada. e.g. 'Could I see the menu, please?'"

🛑 Don’t mention “AI” or “tutor.” Just refer to the role directly.

🔁 Output format (MUST be valid Python list of 4 strings):
[
  "task 1",
  "task 2",
  "task 3",
  "task 4"
]
""")

    user_prompt = HumanMessage(
        content=f'The AI is playing the role of "{role}" in the context: "{context}". Generate tasks.'
    )

    try:
        response = tasks_agent.invoke([system_prompt, user_prompt])
        return eval(response.content)
    except Exception as e:
        print("❌ Error parsing tasks response:", e)
        return []
