# ai/analyzer_agent.py - AGENTE BÁSICO MEJORADO
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from typing import Dict, List
import json

analyzer_model = ChatOpenAI(model="gpt-4o")

def detect_speech_transcription(text: str) -> bool:
    """Detecta si el texto parece provenir de speech-to-text"""
    if not text:
        return False
        
    indicators = [
        len(text.split()) > 10 and text.count('.') == 0,  # Texto largo sin puntos
        text.count(',') == 0 and len(text.split()) > 5,   # Sin comas en texto mediano
        not text[0].isupper(),                            # No empieza en mayúscula
        '?' not in text and any(word in text.lower() for word in ['what', 'how', 'when', 'where', 'why'])
    ]
    return sum(indicators) >= 2

def filter_transcription_errors(feedback_list: List[Dict], is_transcribed: bool) -> List[Dict]:
    """Filtra errores irrelevantes para conversación oral"""
    
    if not is_transcribed:
        return feedback_list
    
    # Keywords que indican errores de transcripción/puntuación
    irrelevant_keywords = [
        "coma", "comma", "punto", "period", "mayúscula", "capital", 
        "signo de interrogación", "question mark", "puntuación", "punctuation",
        "capitaliz", "mayúscul", "punto final"
    ]
    
    filtered = []
    for item in feedback_list:
        explanation = item.get("explanation", "").lower()
        issue = item.get("issue", "").lower() if "issue" in item else ""
        
        # Filtrar si contiene keywords irrelevantes
        text_to_check = f"{explanation} {issue}"
        if not any(keyword in text_to_check for keyword in irrelevant_keywords):
            filtered.append(item)
    
    return filtered

def categorize_feedback_by_severity(feedback_list: List[Dict]) -> Dict[str, List[Dict]]:
    """Organiza feedback por severidad"""
    
    categorized = {
        "high": [],      # Errores que impiden comunicación
        "medium": [],    # Errores notorios pero comprensibles
        "low": []        # Sugerencias de mejora opcional
    }
    
    # Reglas de severidad para el agente básico
    severity_rules = {
        "grammar": "high",
        "vocabulary": "high", 
        "phrasal_verb": "medium",
        "expression": "medium",
        "collocation": "medium"
    }
    
    for item in feedback_list:
        category = item.get("category", "unknown")
        severity = severity_rules.get(category, "medium")
        item["severity"] = severity
        
        # Transformar al nuevo formato
        if "original" not in item:
            item["original"] = item.get("mistake", "")
        if "corrected" not in item:
            item["corrected"] = item.get("suggestion", "")
        if "issue_type" not in item:
            item["issue_type"] = f"{category}_error"
        if "learning_tip" not in item:
            item["learning_tip"] = f"Practica más {category} para mejorar"
        if "examples" not in item:
            item["examples"] = [item.get("suggestion", "")]
        
        categorized[severity].append(item)
    
    return categorized

def generate_summary(prioritized_feedback: Dict[str, List[Dict]]) -> str:
    """Genera un resumen amigable del análisis"""
    
    high_count = len(prioritized_feedback["high"])
    medium_count = len(prioritized_feedback["medium"])
    low_count = len(prioritized_feedback["low"])
    
    if high_count == 0 and medium_count == 0 and low_count == 0:
        return "¡Excelente! Tu inglés suena muy natural 🎉"
    elif high_count == 0 and medium_count == 0:
        return f"¡Muy bien! Solo {low_count} sugerencia(s) menor(es) 👍"
    elif high_count == 0:
        return f"¡Bien! {medium_count} sugerencia(s) para sonar más natural 📈"
    elif high_count == 1:
        return "Una corrección importante y algunas sugerencias opcionales 📝"
    else:
        return f"{high_count} correcciones importantes para mejorar la comunicación 🎯"

feedback_prompt = [
    SystemMessage(content="""
    You are an English coach specialized in helping learners sound more natural and fluent.

    You will receive:
    - The AI's last message (context)
    - The learner's reply

    Your job is to analyze the learner's message and return feedback using JSON format.

    IMPORTANT - FOCUS ON SPOKEN CONVERSATION:
    ❌ DO NOT analyze missing punctuation (commas, periods, question marks)
    ❌ DO NOT analyze capitalization at the beginning of sentences  
    ❌ DO NOT analyze obvious voice transcription errors
    ❌ DO NOT suggest formal writing rules
    
    ✅ DO analyze errors that affect oral communication:
    ✅ Incorrect verb tenses
    ✅ Wrong or unnatural vocabulary
    ✅ Misused phrasal verbs
    ✅ Unnatural expressions

    CATEGORIES (use exactly these):
    - "grammar": Verb tenses, subject-verb agreement, articles, prepositions
    - "vocabulary": Wrong word choice, better alternatives, missing words
    - "phrasal_verb": Incorrect phrasal verbs (take off, give up, etc.)
    - "expression": Idioms, natural expressions, better ways to say something
    - "collocation": Word combinations (make a decision, not take a decision)

    If you find corrections or suggestions relevant for conversation, return a list like this:

    [
        {
            "category": "grammar",
            "mistake": "She don't like pizza",
            "issue": "Incorrect verb conjugation in third person singular",
            "suggestion": "She doesn't like pizza", 
            "explanation": "En tercera persona del singular, el verbo 'do' se conjuga como 'does'. Por eso, debes usar 'doesn't' en lugar de 'don't'."
        }
    ]

    If the learner's message is perfect or only has transcription errors, respond with an empty array: []

    IMPORTANT RULES:
    - Only use the 5 categories listed above
    - DO NOT suggest unnecessary changes if the message is already natural
    - Focus on errors that affect communication or sound unnatural
    - Be supportive and encouraging in explanations
    - Return ONLY valid JSON, no markdown or extra text
    - Give explanations in Spanish
    - If no real errors exist, return empty array []
    - Each error should be a separate object in the array
    """)
]

def analyze_message(ai_text: str, user_text: str) -> str:
    """
    Analiza un mensaje del usuario y retorna feedback en JSON (AGENTE BÁSICO)
    """
    messages = feedback_prompt.copy()
    messages.append(AIMessage(content=ai_text))
    messages.append(HumanMessage(content=user_text))

    try:
        result = analyzer_model.invoke(messages)
        return result.content
    except Exception as e:
        print(f"❌ Error analyzing message: {e}")
        return "[]"

def basic_analysis(ai_text: str, user_text: str) -> Dict:
    """
    Análisis básico que devuelve el mismo formato que el multi-agente
    """
    # Detectar si parece transcripción de voz
    seems_transcribed = detect_speech_transcription(user_text)
    
    # Obtener análisis del modelo
    raw_response = analyze_message(ai_text, user_text)
    
    try:
        # Parsear respuesta
        raw_feedback = json.loads(raw_response)
        if not isinstance(raw_feedback, list):
            raw_feedback = []
    except:
        raw_feedback = []
    
    # Filtrar errores de transcripción
    filtered_feedback = filter_transcription_errors(raw_feedback, seems_transcribed)
    
    # Categorizar por severidad
    prioritized = categorize_feedback_by_severity(filtered_feedback)
    
    # Limitar sugerencias (menos que premium)
    max_suggestions = 2 if seems_transcribed else 3
    final_feedback = (prioritized["high"] + prioritized["medium"] + prioritized["low"])[:max_suggestions]
    
    return {
        "feedback": final_feedback,
        "prioritized": prioritized,
        "is_transcribed": seems_transcribed,
        "total_issues": len(filtered_feedback),
        "summary": generate_summary(prioritized),
        "plan_type": "basic"  # Identificador del plan
    }