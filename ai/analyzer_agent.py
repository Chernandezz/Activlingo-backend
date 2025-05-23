from openai import OpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

analyzer_model = ChatOpenAI(model="gpt-4o")

feedback_prompt = [
    SystemMessage(content="""
You are an advanced English coach specialized in helping learners sound more natural and fluent.
You will receive two short messages:

- The AI's last message (context)
- The learner's reply

Your job is to analyze only the learner's message and return a list of corrections or suggestions.

Use this format:

1. **Category**: grammar / vocabulary / phrasal_verb / idiom / collocation / expression
2. **Your Mistake**: The original sentence or phrase, or section including the mistake, not the whole message.
2. **Issue**: What's incorrect or could be improved.
3. **Suggestion (more natural)**: A better or more fluent way to express it. Be supportive:
- “You're doing great! Try saying: ...”
- “Nice try! A more natural way might be: ...”
4. **Explanation**: Why your suggestion improves the sentence. Give clear, helpful tips.

DO NOT:
- Suggest overly complex or fancy phrases.
- Rewrite the entire message.
- Comment on punctuation unless it affects meaning.

If the message is great, respond with:
> “No major issues found. Great job!”
""")
]

def analyze_message(ai_text: str, user_text: str) -> str:
    messages = feedback_prompt.copy()
    messages.append(AIMessage(content=ai_text))
    messages.append(HumanMessage(content=user_text))

    result = analyzer_model.invoke(messages)
    return result.content
