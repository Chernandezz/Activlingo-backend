# ai/multi_agent_analyzer.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
import json
import asyncio
from typing import List, Dict

model = ChatOpenAI(model="gpt-4o")

def create_specialized_analyzer(category: str, instructions: str):
    """Crea un analizador especializado para una categoría específica"""
    
    system_prompt = f"""
    Eres un especialista en {category} para estudiantes de inglés que practican conversación.
    
    {instructions}
    
    IMPORTANTE - ENFOQUE EN CONVERSACIÓN ORAL:
    ❌ NO analices puntuación faltante (comas, puntos, signos de interrogación)
    ❌ NO analices capitalización al inicio de oraciones  
    ❌ NO analices errores obvios de transcripción de voz
    ❌ NO sugieras reglas de escritura formal
    
    ✅ SÍ analiza errores que afectan la comunicación oral:
    ✅ Tiempos verbales incorrectos
    ✅ Vocabulario incorrecto o poco natural
    ✅ Phrasal verbs mal usados
    ✅ Expresiones poco naturales
    
    FORMATO DE RESPUESTA:
    - Si encuentras errores/sugerencias relevantes para conversación, devuelve:
    [
        {{
            "category": "{category}",
            "original": "texto exacto con error",
            "corrected": "versión corregida",
            "issue_type": "tipo_específico_de_error",
            "severity": "high/medium/low",
            "explanation": "explicación clara en español",
            "learning_tip": "tip útil para recordar la regla",
            "examples": ["ejemplo correcto 1", "ejemplo correcto 2"]
        }}
    ]
    
    - Si no hay errores relevantes para conversación, devuelve: []
    
    IMPORTANTE: Devuelve SOLO JSON válido, sin markdown ni texto extra.
    """
    
    return system_prompt

def get_all_specialists(system_message: str):
    """Define todos los especialistas incluyendo contexto"""
    
    return {
        "grammar": create_specialized_analyzer(
            "grammar",
            """
            Analiza errores gramaticales que afectan la comunicación oral:
            - Tiempos verbales incorrectos
            - Concordancia sujeto-verbo
            - Uso incorrecto de auxiliares (do/does/did)
            - Preposiciones incorrectas
            - Artículos mal usados (a/an/the)
            
            Severity guidelines:
            - "high": Errores que impiden comprensión
            - "medium": Errores notorios pero comprensibles  
            - "low": Mejoras menores
            """
        ),
        
        "vocabulary": create_specialized_analyzer(
            "vocabulary",
            """
            Analiza vocabulario para conversación natural:
            - Palabras incorrectas o inexistentes
            - Mejores alternativas más naturales
            - Palabras que suenan raras en contexto
            - False friends (falsos cognados)
            
            Prioriza sugerencias que hagan sonar más natural al hablante.
            """
        ),
        
        "phrasal_verbs": create_specialized_analyzer(
            "phrasal_verb", 
            """
            Analiza uso de phrasal verbs:
            - Phrasal verbs incorrectos o mal formados
            - Oportunidades para usar phrasal verbs más naturales
            - Separación incorrecta de partículas
            
            Solo sugiere si realmente mejora la naturalidad del inglés hablado.
            """
        ),
        
        "expressions": create_specialized_analyzer(
            "expression",
            """
            Analiza expresiones y naturalidad:
            - Expresiones poco naturales o robóticas
            - Traducciones literales del español
            - Maneras más fluidas de expresar ideas
            - Conectores más naturales
            
            Enfócate en hacer sonar más fluido y natural.
            """
        ),
        
        "collocations": create_specialized_analyzer(
            "collocation",
            """
            Analiza combinaciones de palabras:
            - Combinaciones incorrectas (make a decision vs do a decision)
            - Colocaciones que suenan poco naturales
            - Mejores combinaciones de verbos + sustantivos
            
            Solo sugiere si la colocación suena claramente incorrecta.
            """
        ),
        
        "context_appropriateness": f"""
        Eres un especialista en registro y apropiación contextual del inglés hablado.
        
        CONTEXTO/SITUACIÓN ACTUAL: {system_message}
        
        Analiza si el registro/formalidad es apropiado para esta situación:
        
        Ejemplos:
        - "Good morning, Sir" con amigos → "Hey!" o "What's up?"
        - "Hey dude!" en contexto profesional → "Good morning" 
        - "I would like to request" en chat casual → "Can I..." o "Could you..."
        - Vocabulario muy técnico en conversación casual → alternativas simples
        
        FORMATO DE RESPUESTA:
        - Si el registro NO es apropiado:
        [
            {{
                "category": "context_appropriateness",
                "original": "texto con registro inapropiado",
                "corrected": "alternativa apropiada para el contexto",
                "issue_type": "register_mismatch",
                "severity": "medium",
                "explanation": "explicación de por qué no es apropiado",
                "learning_tip": "cuándo usar cada registro",
                "examples": ["ejemplo apropiado 1", "ejemplo apropiado 2"]
            }}
        ]
        
        - Si el registro es apropiado: []
        
        IMPORTANTE: Solo sugiere si hay una diferencia clara de registro.
        """
    }

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
        learning_tip = item.get("learning_tip", "").lower()
        
        # Filtrar si contiene keywords irrelevantes
        text_to_check = f"{explanation} {issue} {learning_tip}"
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
    
    for item in feedback_list:
        severity = item.get("severity", "medium")
        if severity in categorized:
            categorized[severity].append(item)
        else:
            categorized["medium"].append(item)
    
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

async def analyze_with_all_specialists(system_message: str, ai_text: str, user_text: str) -> List[Dict]:
    """Ejecuta TODOS los especialistas en paralelo"""
    
    specialists = get_all_specialists(system_message)
    
    async def run_specialist(category: str, system_prompt: str):
        try:
            messages = [
                SystemMessage(content=system_prompt),
                AIMessage(content=ai_text),
                HumanMessage(content=user_text)
            ]
            
            result = await model.ainvoke(messages)
            
            # 🔧 ARREGLO: Verificar respuesta vacía
            if not result.content or result.content.strip() == "":
                print(f"⚠️ Empty response from {category}, returning empty array")
                return []
            
            try:
                parsed = json.loads(result.content)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON error in {category}: {result.content}")
                return []
                
        except Exception as e:
            print(f"❌ Error en especialista {category}: {e}")
            return []
    
    # Ejecutar todos los especialistas en paralelo
    tasks = [
        run_specialist(category, prompt) 
        for category, prompt in specialists.items()
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Combinar todos los resultados
    all_feedback = []
    for result in results:
        all_feedback.extend(result)
    
    return all_feedback

async def comprehensive_analysis(system_message: str, ai_text: str, user_text: str) -> Dict:
    """Análisis completo optimizado para conversación oral"""
    
    # Detectar si parece transcripción de voz
    seems_transcribed = detect_speech_transcription(user_text)
    
    # Obtener feedback de todos los especialistas
    raw_feedback = await analyze_with_all_specialists(system_message, ai_text, user_text)
    
    # Filtrar errores irrelevantes para conversación oral
    filtered_feedback = filter_transcription_errors(raw_feedback, seems_transcribed)
    
    # Categorizar por severidad
    prioritized = categorize_feedback_by_severity(filtered_feedback)
    
    # Limitar sugerencias para no abrumar (priorizar las importantes)
    max_suggestions = 3 if seems_transcribed else 5
    final_feedback = (prioritized["high"] + prioritized["medium"] + prioritized["low"])[:max_suggestions]
    
    return {
        "feedback": final_feedback,
        "prioritized": prioritized,
        "is_transcribed": seems_transcribed,
        "total_issues": len(filtered_feedback),
        "summary": generate_summary(prioritized)
    }