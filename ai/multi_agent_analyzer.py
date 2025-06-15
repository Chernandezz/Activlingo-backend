# ai/multi_agent_analyzer_improved.py - VERSIÓN MEJORADA SIN SOBRELAPAMIENTO

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
import json
import asyncio
from typing import List, Dict
import time

model = ChatOpenAI(model="gpt-4o")

def create_specialized_analyzer(category: str, instructions: str, system_context: str = ""):
    """Crea un analizador especializado con contexto del sistema"""
    
    context_section = f"""
    CONTEXTO DE LA CONVERSACIÓN:
    {system_context}
    
    Usa este contexto para determinar qué registro y vocabulario es apropiado.
    """ if system_context.strip() else ""
    
    system_prompt = f"""
    Eres un especialista en {category} para estudiantes de inglés que practican conversación.
    
    {context_section}
    
    {instructions}
    
    IMPORTANTE - ENFOQUE EN CONVERSACIÓN ORAL:
    ❌ NO analices puntuación faltante (comas, puntos, signos de interrogación)
    ❌ NO analices capitalización al inicio de oraciones  
    ❌ NO analices errores obvios de transcripción de voz
    ❌ NO sugieras reglas de escritura formal
    
    ✅ SÍ analiza errores que afectan la comunicación oral:
    ✅ Problemas específicos de tu especialidad
    
    REGLAS DE RESPONSABILIDAD:
    - SOLO corrige errores de tu especialidad específica
    - NO te metas en áreas de otros especialistas
    - Si un error no es claramente de tu área, NO lo reportes
    
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
    """Define todos los especialistas con responsabilidades MUY específicas"""
    
    specialists = {
        "grammar_core": create_specialized_analyzer(
            "grammar",
            """
            SOLO corrige errores gramaticales ESTRUCTURALES básicos:
            - Tiempos verbales incorrectos (I go yesterday → I went yesterday)
            - Concordancia sujeto-verbo (She don't → She doesn't)
            - Artículos básicos faltantes (go to store → go to the store)
            - Orden de palabras básico (very I like → I like very much)
            
            NO TOQUES:
            - Vocabulario (palabras individuales)
            - Expresiones completas
            - Phrasal verbs
            - Registro o formalidad
            
            Severity: high para errores que impiden comprensión, medium para notorios
            """,
            system_message
        ),
        
        "vocabulary_precision": create_specialized_analyzer(
            "vocabulary",
            """
            SOLO corrige palabras INDIVIDUALES incorrectas:
            - Palabras que no existen en inglés
            - False friends obvios (realize → notice cuando significa "darse cuenta")
            - Palabras técnicamente incorrectas en contexto
            
            NO TOQUES:
            - Expresiones completas o frases
            - Gramática
            - Registro/formalidad
            - Combinaciones de palabras (eso es collocations)
            
            Ejemplo: "good mentality" → corrige solo "mentality" a "temperament"
            """,
            system_message
        ),
        
        "phrasal_verbs": create_specialized_analyzer(
            "phrasal_verb",
            """
            SOLO analiza phrasal verbs específicos:
            - Phrasal verbs mal formados (put of → put off)
            - Separación incorrecta de partículas (turn the light on vs turn on the light)
            - Oportunidades claras para usar phrasal verbs más naturales
            
            NO TOQUES:
            - Vocabulario general
            - Expresiones que no sean phrasal verbs
            - Gramática básica
            
            Solo reporta si HAY un phrasal verb involucrado.
            """,
            system_message
        ),
        
        "expressions_fluency": create_specialized_analyzer(
            "expression",
            """
            SOLO mejora fluidez de EXPRESIONES COMPLETAS:
            - Expresiones que suenan robóticas o traducidas literalmente
            - Maneras más fluidas de expresar ideas completas
            - Conectores poco naturales entre ideas
            
            NO TOQUES:
            - Palabras individuales (eso es vocabulary)
            - Gramática básica
            - Phrasal verbs específicos
            
            Enfócate en hacer FRASES COMPLETAS más naturales.
            Ejemplo: "I have good mentality" → "I have a positive attitude"
            """,
            system_message
        ),
        
        "collocations": create_specialized_analyzer(
            "collocation",
            """
            SOLO corrige COMBINACIONES específicas de palabras:
            - Verb + noun combinations (do homework vs make homework)
            - Adjective + noun combinations (strong coffee vs powerful coffee)
            - Preposition combinations (interested in vs interested on)
            
            NO TOQUES:
            - Palabras individuales
            - Expresiones completas largas
            - Gramática básica
            
            Solo reporta combinaciones de 2-3 palabras que suenan incorrectas.
            Ejemplo: "make a decision" vs "do a decision"
            """,
            system_message
        ),
        
        "context_appropriateness": create_specialized_analyzer(
            "context_appropriateness",
            f"""
            CONTEXTO ESPECÍFICO DE ESTA CONVERSACIÓN:
            {system_message}
            
            SOLO analiza si el REGISTRO es apropiado para este contexto específico:
            
            Ejemplos de lo que SÍ debes corregir:
            - Usar "Good morning, Sir" en contexto casual con amigos
            - Usar "Hey dude!" en contexto profesional/formal
            - Vocabulario muy técnico en conversación casual
            - Lenguaje muy informal en contexto profesional
            
            NO TOQUES:
            - Gramática
            - Vocabulario técnicamente correcto
            - Expresiones generales
            
            Solo reporta si hay una diferencia CLARA de registro para este contexto específico.
            
            IMPORTANTE: Si el registro es apropiado para el contexto, devuelve []. 
            No busques problemas donde no los hay.
            """,
            system_message
        )
    }
    
    print(f"🌟 [PREMIUM] Definidos {len(specialists)} especialistas especializados")
    return specialists

def deduplicate_and_prioritize(feedback_list: List[Dict]) -> List[Dict]:
    """
    Elimina duplicados y prioriza las correcciones más importantes
    """
    if not feedback_list:
        return []
    
    print(f"🔍 [PREMIUM] Procesando {len(feedback_list)} sugerencias")
    
    # Agrupar por texto original para detectar sobrelapamiento
    groups = {}
    for item in feedback_list:
        original = item.get('original', '').strip().lower()
        if original not in groups:
            groups[original] = []
        groups[original].append(item)
    
    # Para cada grupo, elegir la mejor sugerencia
    final_suggestions = []
    
    for original_text, suggestions in groups.items():
        if len(suggestions) == 1:
            # Solo una sugerencia, mantenerla
            final_suggestions.append(suggestions[0])
            print(f"🔍 [PREMIUM] Única sugerencia para '{original_text[:30]}': {suggestions[0]['category']}")
        else:
            # Múltiples sugerencias, elegir la mejor
            print(f"🔍 [PREMIUM] {len(suggestions)} sugerencias para '{original_text[:30]}':")
            
            # Prioridad: grammar > vocabulary > expression > collocation > phrasal_verb > context
            priority_order = ["grammar", "vocabulary", "expression", "collocation", "phrasal_verb", "context_appropriateness"]
            
            best_suggestion = None
            for priority_category in priority_order:
                for suggestion in suggestions:
                    if suggestion.get('category') == priority_category:
                        best_suggestion = suggestion
                        break
                if best_suggestion:
                    break
            
            if not best_suggestion:
                best_suggestion = suggestions[0]  # Fallback
            
            final_suggestions.append(best_suggestion)
            print(f"🔍 [PREMIUM] Elegida: {best_suggestion['category']} - {best_suggestion.get('corrected', '')[:30]}")
            
            # Mostrar las descartadas
            for suggestion in suggestions:
                if suggestion != best_suggestion:
                    print(f"🔍 [PREMIUM] Descartada: {suggestion['category']} - {suggestion.get('corrected', '')[:30]}")
    
    print(f"🔍 [PREMIUM] Resultado final: {len(final_suggestions)} sugerencias únicas")
    return final_suggestions

async def analyze_with_all_specialists(system_message: str, ai_text: str, user_text: str) -> List[Dict]:
    """Ejecuta TODOS los especialistas en paralelo con mejor coordinación"""
    
    specialists = get_all_specialists(system_message)
    print(f"🌟 [PREMIUM] Iniciando análisis con especialistas especializados")
    
    async def run_specialist(category: str, system_prompt: str):
        start_time = time.time()
        print(f"🌟 [PREMIUM] Iniciando especialista: {category}")
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                AIMessage(content=ai_text),
                HumanMessage(content=user_text)
            ]
            
            result = await model.ainvoke(messages)
            execution_time = time.time() - start_time
            
            if not result.content or result.content.strip() == "":
                print(f"🌟 [PREMIUM] ⚠️ {category}: Respuesta vacía ({execution_time:.2f}s)")
                return []
            
            print(f"🌟 [PREMIUM] {category}: Respuesta recibida ({execution_time:.2f}s)")
            print(f"🌟 [PREMIUM] {category}: {result.content[:100]}...")
            
            try:
                parsed = json.loads(result.content)
                if isinstance(parsed, list):
                    print(f"🌟 [PREMIUM] ✅ {category}: {len(parsed)} sugerencias encontradas")
                    for i, issue in enumerate(parsed):
                        print(f"🌟 [PREMIUM] {category}[{i+1}]: '{issue.get('original', 'N/A')[:40]}' → '{issue.get('corrected', 'N/A')[:40]}'")
                    return parsed
                else:
                    print(f"🌟 [PREMIUM] ⚠️ {category}: Respuesta no es lista - {type(parsed)}")
                    return []
            except json.JSONDecodeError as e:
                print(f"🌟 [PREMIUM] ❌ {category}: Error JSON - {str(e)[:100]}")
                print(f"🌟 [PREMIUM] {category}: Contenido problemático: {result.content[:200]}")
                return []
                
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"🌟 [PREMIUM] ❌ {category}: Error general ({execution_time:.2f}s) - {e}")
            return []
    
    # Ejecutar todos los especialistas en paralelo
    print(f"🌟 [PREMIUM] Lanzando {len(specialists)} especialistas en paralelo")
    tasks = [
        run_specialist(category, prompt) 
        for category, prompt in specialists.items()
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Combinar todos los resultados
    all_feedback = []
    for i, result in enumerate(results):
        specialist_name = list(specialists.keys())[i]
        print(f"🌟 [PREMIUM] {specialist_name}: Contribuyó {len(result)} sugerencias")
        all_feedback.extend(result)
    
    print(f"🌟 [PREMIUM] Total recolectado: {len(all_feedback)} sugerencias")
    
    # NUEVO: Deduplicar y priorizar
    final_feedback = deduplicate_and_prioritize(all_feedback)
    
    return final_feedback

# Resto de funciones sin cambios (detect_speech_transcription, filter_transcription_errors, etc.)
def detect_speech_transcription(text: str) -> bool:
    if not text:
        return False
    indicators = [
        len(text.split()) > 10 and text.count('.') == 0,
        text.count(',') == 0 and len(text.split()) > 5,
        not text[0].isupper(),
        '?' not in text and any(word in text.lower() for word in ['what', 'how', 'when', 'where', 'why'])
    ]
    return sum(indicators) >= 2

def filter_transcription_errors(feedback_list: List[Dict], is_transcribed: bool) -> List[Dict]:
    if not is_transcribed:
        return feedback_list
    
    irrelevant_keywords = [
        "coma", "comma", "punto", "period", "mayúscula", "capital", 
        "signo de interrogación", "question mark", "puntuación", "punctuation",
        "capitaliz", "mayúscul", "punto final"
    ]
    
    filtered = []
    for item in feedback_list:
        explanation = item.get("explanation", "").lower()
        if not any(keyword in explanation for keyword in irrelevant_keywords):
            filtered.append(item)
    
    return filtered

def categorize_feedback_by_severity(feedback_list: List[Dict]) -> Dict[str, List[Dict]]:
    categorized = {"high": [], "medium": [], "low": []}
    
    for item in feedback_list:
        severity = item.get("severity", "medium")
        if severity in categorized:
            categorized[severity].append(item)
        else:
            categorized["medium"].append(item)
    
    return categorized

def generate_summary(prioritized_feedback: Dict[str, List[Dict]]) -> str:
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

async def comprehensive_analysis(system_message: str, ai_text: str, user_text: str) -> Dict:
    """Análisis completo mejorado para conversación oral"""
    
    print("🌟 [PREMIUM] === STARTING IMPROVED COMPREHENSIVE ANALYSIS ===")
    print(f"🌟 [PREMIUM] System context: {system_message[:100]}...")
    print(f"🌟 [PREMIUM] User text: {user_text}")
    
    # Detectar si parece transcripción de voz
    seems_transcribed = detect_speech_transcription(user_text)
    
    # Obtener feedback de todos los especialistas (mejorados)
    print("🌟 [PREMIUM] Fase 1: Ejecutando especialistas mejorados")
    raw_feedback = await analyze_with_all_specialists(system_message, ai_text, user_text)
    
    # Filtrar errores irrelevantes para conversación oral
    print("🌟 [PREMIUM] Fase 2: Filtrando errores de transcripción")
    filtered_feedback = filter_transcription_errors(raw_feedback, seems_transcribed)
    
    # Categorizar por severidad
    print("🌟 [PREMIUM] Fase 3: Categorizando por severidad")
    prioritized = categorize_feedback_by_severity(filtered_feedback)
    
    # Limitar sugerencias para no abrumar (máximo 4 de alta calidad)
    max_suggestions = 3 if seems_transcribed else 4
    final_feedback = (prioritized["high"] + prioritized["medium"] + prioritized["low"])[:max_suggestions]
    
    print(f"🌟 [PREMIUM] Fase 4: Limitado a {len(final_feedback)} sugerencias finales (max: {max_suggestions})")
    
    # Mostrar resultado final
    if final_feedback:
        print("🌟 [PREMIUM] SUGERENCIAS FINALES:")
        for i, item in enumerate(final_feedback, 1):
            print(f"🌟 [PREMIUM] [{i}] {item.get('category')}: '{item.get('original', '')[:40]}' → '{item.get('corrected', '')[:40]}'")
    
    result = {
        "feedback": final_feedback,
        "prioritized": prioritized,
        "is_transcribed": seems_transcribed,
        "total_issues": len(filtered_feedback),
        "summary": generate_summary(prioritized)
    }
    
    print("🌟 [PREMIUM] === IMPROVED COMPREHENSIVE ANALYSIS COMPLETE ===")
    return result