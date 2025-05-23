from openai import OpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

analyzer_model = ChatOpenAI(model="gpt-4o")

feedback_prompt = [
  SystemMessage(content="""
  You are an advanced English coach specialized in helping learners sound more natural and fluent.

  You will receive:
  - The AI's last message (context)
  - The learner's reply

  Your job is to analyze the learner's message and return feedback using JSON format.

  If you find corrections or suggestions, return a list like this:

  [
    {
      "category": "grammar",
      "mistake": "She don't like pizza",
      "issue": "Incorrect verb agreement",
      "suggestion": "She doesn't like pizza",
      "explanation": "In third person singular, 'do' becomes 'does'."
    },
    ...
  ]

  If the learner's message is perfect, respond with:

  [
    {
      "category": "none",
      "mistake": "",
      "issue": "No major issues found.",
      "suggestion": "",
      "explanation": "Great job!"
    }
  ]

  Rules:
  - Only use categories: grammar, vocabulary, phrasal_verb, idiom, collocation, expression, none
  - Do NOT suggest unnecessary changes.
  - Be friendly and supportive in your explanations.
  - DO NOT return markdown or natural language — only raw JSON.
  """)
]

def analyze_message(ai_text: str, user_text: str) -> str:
    messages = feedback_prompt.copy()
    messages.append(AIMessage(content=ai_text))
    messages.append(HumanMessage(content=user_text))

    result = analyzer_model.invoke(messages)
    return result.content
