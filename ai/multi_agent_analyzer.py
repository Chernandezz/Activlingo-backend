# ai/multi_agent_analyzer.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from typing import List
import json

model = ChatOpenAI(model="gpt-4o")

def get_prompt(category: str, system_instruction: str):
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        AIMessage(content="{ai_message}"),
        HumanMessage(content="{user_message}")
    ])

analyzers = {
    "grammar": get_prompt("grammar", """
    You are a grammar tutor. Your task is to find grammar issues in the student's message.
    Provide only grammar-related feedback in the specified JSON format.
    If there are no issues, return the 'none' template.
    """),

    "vocabulary": get_prompt("vocabulary", """
    You are a vocabulary coach. Look for poor or inaccurate word choices.
    Suggest more appropriate or natural vocabulary if needed, following the same format.
    If everything looks good, return the 'none' template.
    """),

    "phrasal_verb": get_prompt("phrasal_verb", """
    You specialize in phrasal verbs. Suggest one if it would sound more natural or be appropriate in context.
    If there's no opportunity, respond with the 'none' template.
    """),

    "idiom": get_prompt("idiom", """
    You are an idioms expert. Only suggest an idiom if it's commonly used and perfectly fits the context.
    If not, return a positive feedback with category 'none'.
    """),

    "collocation": get_prompt("collocation", """
    You are a collocations coach. Identify unnatural combinations of words and suggest better collocations.
    Follow the JSON format or use the 'none' template.
    """),

    "expression": get_prompt("expression", """
    You help learners sound more fluent by suggesting more natural expressions.
    Only suggest better expressions if the message sounds robotic or awkward.
    If fluent, return the 'none' template.
    """),
}

analyzer_chain = RunnableParallel({k: prompt | model for k, prompt in analyzers.items()})



async def analyze_with_multiple_agents(ai_text: str, user_text: str) -> list[dict]:
    result = await analyzer_chain.ainvoke({
        "ai_message": ai_text,
        "user_message": user_text
    })

    all_entries = []
    for raw_json in result.values():
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, list):
                all_entries.extend(parsed)
        except Exception as e:
            print("⚠️ Error parsing one analyzer result:", e)
            continue

    return all_entries
