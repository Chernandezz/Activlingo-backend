from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import os
from dotenv import load_dotenv

load_dotenv()

dictionary_agent = ChatOpenAI(
    model="gpt-3.5-turbo-0125"
)

def get_definitions_from_gpt(word: str) -> list[dict]:
    system_prompt = SystemMessage(content="""
You are a professional English dictionary assistant. When given a word or phrase, respond STRICTLY with a JSON list of definitions following this format:

[
  {
    "meaning": "clear definition (max 12 words)",
    "example": "natural sentence with the word (optional)",
    "part_of_speech": "noun/verb/adjective/adverb/phrasal_verb/idiom",
    "usage_context": "general|business|travel|slang|academic", 
    "is_idiomatic": true/false,
    "synonyms": ["synonym1", "synonym2"], 
    "source": "ChatGPT"
  }
]

✅ Instructions:
1. Include 2 to 5 **distinct definitions** only.
2. Use simple English unless the word is advanced.
3. Always include synonyms if available.
4. If there's no good example, use an empty string: ""
5. Use valid JSON. No extra text before or after the JSON.
6. If no definitions are found, return an empty list: []
7. If the word is unknown, suggest similar alternatives in the JSON.
""")


    user_prompt = HumanMessage(content=f'Define the word or phrase: "{word}"')

    try:
        response = dictionary_agent.invoke([system_prompt, user_prompt])
        return json.loads(response.content.strip())
    except Exception as e:
        print("❌ Error parsing GPT response:", e)
        return []
