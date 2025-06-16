# ai/analyzer_agent.py - BASIC ANALYZER SÚPER PODEROSO

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from typing import Dict, List
import json
import time

analyzer_model = ChatOpenAI(model="gpt-4o")

def detect_speech_transcription(text: str) -> bool:
    """Detecta si el texto parece provenir de speech-to-text"""
    if not text:
        return False
        
    indicators = [
        len(text.split()) > 10 and text.count('.') == 0,
        text.count(',') == 0 and len(text.split()) > 5,
        not text[0].isupper(),
        '?' not in text and any(word in text.lower() for word in ['what', 'how', 'when', 'where', 'why'])
    ]
    detected = sum(indicators) >= 2
    print(f"🔧 [POWERFUL] Speech transcription: {detected} ({sum(indicators)}/4 indicators)")
    return detected

def filter_transcription_errors(feedback_list: List[Dict], is_transcribed: bool) -> List[Dict]:
    """Filtra errores irrelevantes para conversación oral"""
    if not is_transcribed:
        return feedback_list
    
    irrelevant_keywords = [
        "coma", "comma", "punto", "period", "mayúscula", "capital", 
        "signo de interrogación", "question mark", "puntuación", "punctuation"
    ]
    
    filtered = []
    for item in feedback_list:
        explanation = item.get("explanation", "").lower()
        if not any(keyword in explanation for keyword in irrelevant_keywords):
            filtered.append(item)
        else:
            print(f"🔧 [POWERFUL] Filtered punctuation error: {item.get('category')}")
    
    return filtered

def categorize_feedback_by_severity(feedback_list: List[Dict]) -> Dict[str, List[Dict]]:
    """Organiza feedback por severidad con reglas inteligentes"""
    
    categorized = {"high": [], "medium": [], "low": []}
    
    # Reglas de severidad inteligentes
    severity_rules = {
        "grammar": "high",                  # Tiempos verbales, concordancia
        "vocabulary": "high",               # Palabras incorrectas
        "context_appropriateness": "medium", # Registro formal/informal
        "collocation": "medium",            # Combinaciones naturales
        "phrasal_verb": "medium",           # Verbos compuestos
        "expression": "low"                 # Fluidez general
    }
    
    for item in feedback_list:
        category = item.get("category", "unknown")
        
        # Usar severidad del modelo si existe, sino aplicar reglas
        severity = item.get("severity", severity_rules.get(category, "medium"))
        item["severity"] = severity
        
        # Normalizar formato y usar learning_tip del modelo
        if "original" not in item:
            item["original"] = item.get("mistake", "")
        if "corrected" not in item:
            item["corrected"] = item.get("suggestion", "")
        if "issue_type" not in item:
            item["issue_type"] = item.get("issue", f"{category}_error")
        
        # 🎯 USAR LEARNING TIP DEL MODELO (no hardcoded)
        if "learning_tip" not in item or not item["learning_tip"]:
            # Fallback simple si el modelo no generó learning_tip
            item["learning_tip"] = f"💡 Practica más {category} para mejorar tu fluidez"
        
        if "examples" not in item:
            item["examples"] = [item.get("suggestion", "")]
        
        categorized[severity].append(item)
    
    print(f"🔧 [POWERFUL] Severity: high={len(categorized['high'])}, medium={len(categorized['medium'])}, low={len(categorized['low'])}")
    return categorized

def generate_summary(prioritized_feedback: Dict[str, List[Dict]]) -> str:
    """Genera resumen inteligente del análisis"""
    
    high_count = len(prioritized_feedback["high"])
    medium_count = len(prioritized_feedback["medium"])
    low_count = len(prioritized_feedback["low"])
    
    if high_count == 0 and medium_count == 0 and low_count == 0:
        return "¡Excelente! Tu inglés suena muy natural 🎉"
    elif high_count == 0 and medium_count == 0:
        return f"¡Muy bien! Solo {low_count} sugerencia(s) de estilo 👍"
    elif high_count == 0:
        return f"¡Bien! {medium_count} sugerencia(s) para sonar más natural 📈"
    elif high_count == 1:
        return "Una corrección importante y algunas sugerencias opcionales 📝"
    else:
        return f"{high_count} correcciones importantes para mejorar la comunicación 🎯"

# 🚀 PROMPT SÚPER PODEROSO PERO COMPACTO - MEJORADO
def create_powerful_prompt() -> str:
    return """You are an expert English conversation coach. Analyze the learner's message for ALL types of spoken English errors.

🎯 CRITICAL: Detect errors across ALL categories, not just expressions!

❌ IGNORE: punctuation, capitalization, obvious transcription errors
✅ ANALYZE: Check EVERY category systematically

📋 CATEGORIES (check ALL of these):

🔴 "grammar" - PRIORITY CHECK:
- Wrong verb tenses (I go yesterday → I went yesterday)
- Subject-verb disagreement (She don't → She doesn't)  
- Missing/wrong articles (go to store → go to the store)
- Wrong prepositions (good in math → good at math)

🟠 "vocabulary" - PRIORITY CHECK:
- Non-existent words (mentality → temperament)
- Wrong word choice (realize vs notice)
- False friends from Spanish

🔵 "phrasal_verb" - PRIORITY CHECK:
- Missing phrasal verbs (I woke at 7am → I woke up at 7am)
- Wrong phrasal verbs (take of → take off)
- Opportunities for natural phrasal verbs

🟢 "collocation" - PRIORITY CHECK:
- Wrong verb-noun combinations (do a decision → make a decision)
- Unnatural word pairs (strong tea → strong coffee, heavy rain)
- Preposition collocations (different of → different from)

🟣 "context_appropriateness" - PRIORITY CHECK:
- Too formal for casual context (I would like to request → Can I have)
- Too informal for formal context (Hey dude → Hello sir)

🟡 "expression" - LAST CHECK:
- Only after checking all above categories
- Unnatural phrases that don't fit other categories

🔍 ANALYSIS PROCESS:
1. Check grammar errors first (tenses, articles, agreement)
2. Check vocabulary (wrong individual words)
3. Check collocations (word combinations)
4. Check phrasal verbs (compound verbs)
5. Check context appropriateness (formality)
6. Finally check expressions (general fluency)

⚡ RULES:
- Max 4 suggestions total
- Must check ALL categories systematically  
- Don't default to "expression" - be specific!
- Explanations in Spanish
- Include helpful learning tip for each error

🎯 OUTPUT: JSON array with learning_tip field. If perfect, return []

EXAMPLE showing category diversity:
[
  {
    "category": "grammar",
    "mistake": "I go to store yesterday",
    "suggestion": "I went to the store yesterday", 
    "explanation": "Usa pasado simple 'went' para acciones terminadas. También necesitas el artículo 'the' antes de 'store'.",
    "learning_tip": "🕐 Regla: Para pasado simple, agrega -ed a verbos regulares (walk → walked). Para 'go' es irregular: go → went",
    "issue": "past_tense_and_article_error"
  },
  {
    "category": "collocation", 
    "mistake": "make homework",
    "suggestion": "do homework",
    "explanation": "Se dice 'do homework', no 'make homework'. Es una colocación fija en inglés.",
    "learning_tip": "🎯 Truco: MAKE = crear algo nuevo (make a cake). DO = actividades/tareas (do homework, do exercise)",
    "issue": "verb_noun_collocation"
  },
  {
    "category": "vocabulary",
    "mistake": "good mentality",
    "suggestion": "good temperament", 
    "explanation": "'Mentality' no se usa así en inglés. 'Temperament' es mejor para personalidad.",
    "learning_tip": "🧠 Memoria: Temperament = carácter natural de una persona. Mentality = forma de pensar grupal",
    "issue": "wrong_word_choice"
  }
]

🎓 LEARNING TIP GUIDELINES:
- Start with emoji (🕐📝🎯🧠💡🔗⚡)
- Give practical rules or memory tricks
- Keep it short and actionable
- Make it different from the explanation
- Focus on "how to remember" or "quick rule"

⚠️ IMPORTANT: Don't classify everything as "expression" - be precise with categories!"""

def analyze_message(ai_text: str, user_text: str) -> str:
    """Analiza mensaje con prompt súper poderoso"""
    print(f"🔧 [POWERFUL] Analyzing: '{user_text[:60]}{'...' if len(user_text) > 60 else ''}'")
    
    messages = [
        SystemMessage(content=create_powerful_prompt()),
        AIMessage(content=ai_text),
        HumanMessage(content=user_text)
    ]

    try:
        start_time = time.time()
        result = analyzer_model.invoke(messages)
        execution_time = time.time() - start_time
        
        print(f"🔧 [POWERFUL] Response in {execution_time:.2f}s")
        print(f"🔧 [POWERFUL] Raw: {result.content[:150]}...")
        
        return result.content
    except Exception as e:
        print(f"🔧 [POWERFUL] ❌ Error: {e}")
        return "[]"

def deduplicate_suggestions(feedback_list: List[Dict]) -> List[Dict]:
    """Elimina sugerencias duplicadas o muy similares"""
    if len(feedback_list) <= 1:
        return feedback_list
    
    deduplicated = []
    seen_mistakes = set()
    
    for item in feedback_list:
        mistake_key = item.get('mistake', '').lower().strip()
        
        # Si ya vimos un error muy similar, saltar
        if any(abs(len(mistake_key) - len(seen)) < 3 and 
               mistake_key in seen or seen in mistake_key 
               for seen in seen_mistakes):
            print(f"🔧 [POWERFUL] Skipped duplicate: {mistake_key}")
            continue
        
        seen_mistakes.add(mistake_key)
        deduplicated.append(item)
    
    print(f"🔧 [POWERFUL] Deduplicated: {len(feedback_list)} → {len(deduplicated)}")
    return deduplicated

def prioritize_by_impact(feedback_list: List[Dict]) -> List[Dict]:
    """Prioriza errores por impacto en la comunicación"""
    
    # Palabras clave que indican alto impacto
    high_impact_keywords = [
        "incorrect", "wrong", "doesn't exist", "not a word", 
        "confusing", "unclear", "impedes", "prevents"
    ]
    
    medium_impact_keywords = [
        "unnatural", "better", "more natural", "sounds odd", 
        "unusual", "formal", "informal"
    ]
    
    for item in feedback_list:
        explanation = item.get('explanation', '').lower()
        issue = item.get('issue', '').lower()
        text_to_check = f"{explanation} {issue}"
        
        # Asignar prioridad basada en contenido
        if any(keyword in text_to_check for keyword in high_impact_keywords):
            item['priority'] = 1  # Alta
        elif any(keyword in text_to_check for keyword in medium_impact_keywords):
            item['priority'] = 2  # Media
        else:
            item['priority'] = 3  # Baja
    
    # Ordenar por prioridad
    sorted_feedback = sorted(feedback_list, key=lambda x: x.get('priority', 3))
    
    if sorted_feedback:
        print(f"🔧 [POWERFUL] Prioritized by impact: {[item.get('priority', 3) for item in sorted_feedback[:3]]}")
    
    return sorted_feedback

def basic_analysis(ai_text: str, user_text: str) -> Dict:
    """
    🚀 ANÁLISIS BÁSICO SÚPER PODEROSO
    """
    print(f"🔧 [POWERFUL] === STARTING POWERFUL BASIC ANALYSIS ===")
    
    # Detectar transcripción de voz
    seems_transcribed = detect_speech_transcription(user_text)
    
    # Obtener análisis poderoso
    print(f"🔧 [POWERFUL] Sending to powerful model...")
    raw_response = analyze_message(ai_text, user_text)
    
    try:
        # Parsear respuesta
        raw_feedback = json.loads(raw_response)
        if not isinstance(raw_feedback, list):
            print(f"🔧 [POWERFUL] ⚠️ Non-list response, converting")
            raw_feedback = []
        print(f"🔧 [POWERFUL] Parsed {len(raw_feedback)} suggestions")
    except Exception as e:
        print(f"🔧 [POWERFUL] ❌ JSON error: {e}")
        raw_feedback = []
    
    # Mostrar sugerencias encontradas
    if raw_feedback:
        print(f"🔧 [POWERFUL] Found suggestions:")
        for i, item in enumerate(raw_feedback, 1):
            cat = item.get('category', 'N/A')
            mistake = item.get('mistake', 'N/A')[:40]
            suggestion = item.get('suggestion', 'N/A')[:40]
            print(f"🔧 [POWERFUL]   [{i}] {cat}: '{mistake}' → '{suggestion}'")
    
    # 🔧 Filtrar errores de transcripción
    filtered_feedback = filter_transcription_errors(raw_feedback, seems_transcribed)
    
    # 🎯 Deduplicar sugerencias similares
    deduplicated_feedback = deduplicate_suggestions(filtered_feedback)
    
    # 📊 Priorizar por impacto
    prioritized_raw = prioritize_by_impact(deduplicated_feedback)
    
    # 📋 Categorizar por severidad
    prioritized = categorize_feedback_by_severity(prioritized_raw)
    
    # 🎯 Limitar a las más importantes (inteligentemente)
    if seems_transcribed:
        max_suggestions = 2  # Menos sugerencias para voz
    else:
        max_suggestions = 4  # Más para texto escrito
    
    # Priorizar: high → medium → low
    final_feedback = (prioritized["high"] + prioritized["medium"] + prioritized["low"])[:max_suggestions]
    
    print(f"🔧 [POWERFUL] Final: {len(final_feedback)} suggestions (max: {max_suggestions})")
    
    # Mostrar sugerencias finales
    if final_feedback:
        print(f"🔧 [POWERFUL] Final suggestions:")
        for i, item in enumerate(final_feedback, 1):
            print(f"🔧 [POWERFUL]   [{i}] {item.get('category')}: {item.get('mistake', '')[:30]} → {item.get('suggestion', '')[:30]}")
    
    # Generar resumen
    summary = generate_summary(prioritized)
    
    result = {
        "feedback": final_feedback,
        "prioritized": prioritized,
        "is_transcribed": seems_transcribed,
        "total_issues": len(filtered_feedback),
        "summary": summary,
        "plan_type": "basic_powerful"
    }
    
    print(f"🔧 [POWERFUL] === POWERFUL ANALYSIS COMPLETE ===")
    return result