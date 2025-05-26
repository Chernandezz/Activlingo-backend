from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import os
from dotenv import load_dotenv

load_dotenv()

dictionary_agent = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0.3
)

def get_definitions_from_gpt(word: str) -> list[dict]:
    system_prompt = SystemMessage(content="""
You are a dictionary assistant. When given a word or phrase, respond with a JSON list of relevant definitions in this exact format:

[
  {
    "meaning": "clear definition...",
    "example": "short example in natural English...",
    "part_of_speech": "noun | verb | adjective | etc.",
    "source": "ChatGPT"
  }
]

🧠 Instructions:
- Include 1 to 5 definitions MAX.
- Use plain English.
- Avoid outdated or overly technical meanings.
- If it's a phrasal verb or idiom, treat it naturally.

Always return only the JSON, nothing else.
""")

    user_prompt = HumanMessage(content=f'Define the word or phrase: "{word}"')

    try:
        response = dictionary_agent.invoke([system_prompt, user_prompt])
        return json.loads(response.content.strip())
    except Exception as e:
        print("❌ Error parsing GPT response:", e)
        return []
