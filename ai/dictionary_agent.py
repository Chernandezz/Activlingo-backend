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
You are a professional English dictionary assistant. When given a word or phrase, respond STRICTLY with a JSON list of definitions following these rules:

[
  {
    "meaning": "clear definition (max 10 words)",
    "example": "natural example sentence (max 15 words)",
    "part_of_speech": "noun/verb/adjective/adverb/phrasal_verb/idiom",
    "usage_context": "general|business|travel|slang|academic", 
    "is_idiomatic": true/false,
    "synonyms": ["word1", "word2"], 
    "source": "ChatGPT"
  }
]

🧠 **Instructions**:
1. Include ONLY distinct meanings (avoid redundant variations).
2. For phrasal verbs/idioms, set `is_idiomatic: true`.
3. Limit to 3-5 definitions MAX.
4. Use simple English (A2-B2 level unless the word is advanced).
5. Always return valid JSON, no additional text.
                                  
6. If no definitions found, return an empty list: `[]`. or suggest similar words. for example if the user asked for idolent, you can suggest, indolent, indolence, indolently, indolentia, etc.
""")

    user_prompt = HumanMessage(content=f'Define the word or phrase: "{word}"')

    try:
        response = dictionary_agent.invoke([system_prompt, user_prompt])
        return json.loads(response.content.strip())
    except Exception as e:
        print("❌ Error parsing GPT response:", e)
        return []
