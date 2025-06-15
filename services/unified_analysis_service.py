# services/unified_analysis_service.py - SERVICIO UNIFICADO FINAL
from config.supabase_client import supabase
from schemas.chat_analysis import MessageAnalysis, LanguageAnalysisPoint
from uuid import UUID
import json
from typing import Dict, List

# Importar ambos analizadores
from ai.multi_agent_analyzer import comprehensive_analysis as premium_analysis
from ai.analyzer_agent import basic_analysis

# Categorías válidas para validación
VALID_CATEGORIES = {"grammar", "vocabulary", "phrasal_verb", "expression", "collocation", "context_appropriateness"}

def get_user_plan_type(user_id: UUID) -> str:
    """
    Obtiene el tipo de plan del usuario desde la base de datos
    """
    try:
        # Consultar el plan del usuario
        response = (
            supabase
            .table("users")  # O la tabla donde tengas los planes
            .select("subscription_type, plan_type")
            .eq("id", str(user_id))
            .single()
            .execute()
        )
        
        if response.data:
            # Asumir que tienes campos como "premium", "basic", etc.
            plan = response.data.get("subscription_type", "basic") or response.data.get("plan_type", "basic")
            return plan.lower()
        
        return "basic"  # Default a básico
        
    except Exception as e:
        print(f"⚠️ Error getting user plan: {e}")
        return "basic"  # Default a básico en caso de error

def get_system_message_from_chat(chat_id: UUID) -> str:
    """
    Obtiene el system message de un chat específico
    """
    try:
        # Buscar en los mensajes del chat el mensaje de tipo "system"
        response = (
            supabase
            .table("messages")
            .select("content")
            .eq("chat_id", str(chat_id))
            .eq("sender", "system")
            .limit(1)
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            return response.data[0]["content"]
        
        # Fallback: buscar en la tabla chats si tiene un campo system_message
        chat_response = (
            supabase
            .table("chats")
            .select("system_message, context")
            .eq("id", str(chat_id))
            .single()
            .execute()
        )
        
        if chat_response.data:
            return chat_response.data.get("system_message", "") or chat_response.data.get("context", "")
        
        return "You are a helpful English conversation partner."
        
    except Exception as e:
        print(f"⚠️ Error getting system message: {e}")
        return "You are a helpful English conversation partner."

async def analyze_message_by_plan(
    user_id: UUID, 
    system_message: str, 
    ai_text: str, 
    user_text: str
) -> Dict:
    """
    Ejecuta el análisis apropiado según el plan del usuario
    """
    try:
        # Obtener tipo de plan del usuario
        # plan_type = get_user_plan_type(user_id)
        # print(f"🔍 User {user_id} has plan: {plan_type}")
        
        plan_type = 'premium'  # Para pruebas, usar siempre premium
        # Ejecutar análisis según el plan
        if plan_type in ["premium", "pro", "unlimited"]:
            print("🌟 Executing PREMIUM multi-agent analysis")
            analysis_result = await premium_analysis(system_message, ai_text, user_text)
            analysis_result["plan_type"] = "premium"
        else:
            print("🔧 Executing BASIC single-agent analysis")
            analysis_result = basic_analysis(ai_text, user_text)
            analysis_result["plan_type"] = "basic"
        
        return analysis_result
        
    except Exception as e:
        print(f"❌ Error in analyze_message_by_plan: {e}")
        # Fallback a análisis básico
        fallback_result = basic_analysis(ai_text, user_text)
        fallback_result["plan_type"] = "basic_fallback"
        return fallback_result

def save_analysis(message_id: UUID, entries: List[Dict]) -> None:
    """
    Guarda análisis de un mensaje, filtrando entradas inválidas
    """
    if not entries:
        return

    valid_entries = []
    for entry in entries:
        # Adaptar al nuevo formato si viene del multi-agente
        mistake = entry.get('original', '') or entry.get('mistake', '')
        suggestion = entry.get('corrected', '') or entry.get('suggestion', '')
        explanation = entry.get('explanation', '')
        category = entry.get('category', '')
        issue = entry.get('issue', '') or entry.get('issue_type', '')
        
        # Validar campos requeridos
        if not all([
            mistake.strip(),
            suggestion.strip(), 
            explanation.strip(),
            category in VALID_CATEGORIES
        ]):
            continue
            
        # Filtrar "no errors" responses
        if (
            mistake in ["", "EMPTY", "No errors found"] 
            or category == "none"
            or "no se encontraron errores" in explanation.lower()
        ):
            continue

        valid_entries.append({
            "message_id": str(message_id),
            "category": category,
            "mistake": mistake.strip(),
            "issue": issue.strip(),
            "suggestion": suggestion.strip(),
            "explanation": explanation.strip()
        })

    if not valid_entries:
        print(f"✅ No valid analysis entries for message {message_id}")
        return

    try:
        result = supabase.table("message_analysis").insert(valid_entries).execute()
        print(f"✅ Saved {len(valid_entries)} analysis entries for message {message_id}")
    except Exception as e:
        print(f"⚠️ Error saving analysis entries: {e}")

def get_analysis_by_chat_id(chat_id: UUID) -> List[MessageAnalysis]:
    """
    Obtiene análisis siguiendo la relación correcta chat → mensajes → análisis
    """
    try:
        # 1. Obtener todos los mensajes del chat
        messages_response = (
            supabase
            .table("messages")
            .select("id")
            .eq("chat_id", str(chat_id))
            .execute()
        )
        
        if not messages_response.data:
            print(f"📭 No messages found for chat {chat_id}")
            return []
        
        message_ids = [msg["id"] for msg in messages_response.data]
        print(f"📨 Found {len(message_ids)} messages in chat {chat_id}")
        
        # 2. Obtener todos los análisis para esos mensajes
        analysis_response = (
            supabase
            .table("message_analysis")
            .select("*")
            .in_("message_id", message_ids)
            .order("created_at", desc=False)
            .execute()
        )
        
        analysis_list = [MessageAnalysis(**entry) for entry in analysis_response.data or []]
        print(f"✅ Retrieved {len(analysis_list)} analysis points for chat {chat_id}")
        return analysis_list
        
    except Exception as e:
        print(f"⚠️ Error fetching analysis for chat {chat_id}: {e}")
        return []

def get_user_dictionary_words_in_chat(user_id: UUID, chat_id: UUID) -> List[Dict]:
    """
    Detecta palabras del diccionario del usuario que fueron usadas en el chat
    """
    try:
        # 1. Obtener todas las palabras del diccionario del usuario
        dict_response = (
            supabase
            .table("user_dictionary")
            .select("word, meaning, usage_count")
            .eq("user_id", str(user_id))
            .execute()
        )
        
        user_words = {row["word"].lower(): row for row in dict_response.data or []}
        
        if not user_words:
            print(f"📚 No dictionary words found for user {user_id}")
            return []
        
        # 2. Obtener todos los mensajes del usuario en este chat
        messages_response = (
            supabase
            .table("messages")
            .select("content")
            .eq("chat_id", str(chat_id))
            .eq("sender", "human")
            .execute()
        )
        
        if not messages_response.data:
            print(f"💬 No user messages found in chat {chat_id}")
            return []
        
        # 3. Extraer todas las palabras del chat
        chat_text = " ".join([msg["content"] for msg in messages_response.data])
        chat_words = set()
        
        for word in chat_text.split():
            clean_word = word.lower().strip(".,!?;:\"'()[]{}").strip()
            if len(clean_word) > 2:
                chat_words.add(clean_word)
        
        # 4. Encontrar coincidencias
        used_words = []
        for chat_word in chat_words:
            if chat_word in user_words:
                used_words.append({
                    "word": chat_word,
                    "meaning": user_words[chat_word]["meaning"],
                    "usage_count": user_words[chat_word]["usage_count"]
                })
        
        print(f"✅ Found {len(used_words)} dictionary words used in chat {chat_id}")
        return used_words
        
    except Exception as e:
        print(f"⚠️ Error finding dictionary words in chat: {e}")
        return []

def process_ai_analysis_response(ai_response: str) -> List[Dict]:
    """
    Procesa la respuesta del AI y la convierte en lista de diccionarios
    """
    try:
        cleaned = ai_response.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        analysis_data = json.loads(cleaned)
        
        if not isinstance(analysis_data, list):
            print(f"⚠️ AI response is not a list: {type(analysis_data)}")
            return []
            
        return analysis_data
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing AI response as JSON: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error processing AI response: {e}")
        return []

def calculate_chat_stats(analysis_points: List[MessageAnalysis]) -> Dict:
    """
    Calcula estadísticas del chat
    """
    if not analysis_points:
        return {
            "total_errors": 0,
            "by_category": {},
            "overall_score": 100,
            "improvement_areas": []
        }
    
    # Contar por categoría
    category_counts = {}
    for point in analysis_points:
        category = point.category
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Calcular score
    total_errors = len(analysis_points)
    penalty_per_error = 3
    overall_score = max(50, 100 - (total_errors * penalty_per_error))
    
    # Áreas de mejora
    improvement_areas = sorted(
        category_counts.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:3]
    
    return {
        "total_errors": total_errors,
        "by_category": category_counts,
        "overall_score": overall_score,
        "improvement_areas": [area[0] for area in improvement_areas]
    }

def debug_chat_analysis(chat_id: UUID) -> Dict:
    """
    Función de debug para verificar qué datos existen
    """
    try:
        # Verificar que el chat existe
        chat_response = (
            supabase
            .table("chats")
            .select("id, title")
            .eq("id", str(chat_id))
            .execute()
        )
        
        if not chat_response.data:
            return {"error": f"Chat {chat_id} not found"}
        
        # Verificar mensajes del chat
        messages_response = (
            supabase
            .table("messages")
            .select("id, sender, content")
            .eq("chat_id", str(chat_id))
            .execute()
        )
        
        messages = messages_response.data or []
        message_ids = [msg["id"] for msg in messages]
        
        # Verificar análisis existentes
        if message_ids:
            analysis_response = (
                supabase
                .table("message_analysis")
                .select("id, message_id, category, mistake")
                .in_("message_id", message_ids)
                .execute()
            )
            analysis = analysis_response.data or []
        else:
            analysis = []
        
        return {
            "chat_exists": bool(chat_response.data),
            "messages_count": len(messages),
            "messages": messages[:5],
            "analysis_count": len(analysis),
            "analysis": analysis[:5],
            "message_ids": message_ids
        }
        
    except Exception as e:
        return {"error": str(e)}