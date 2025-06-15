# services/analysis_service.py - VERSIÓN SIMPLIFICADA SOLO BASIC

from config.supabase_client import supabase
from schemas.chat_analysis import MessageAnalysis, LanguageAnalysisPoint
from uuid import UUID
import json
from typing import Dict, List

# Solo importar el basic analyzer
from ai.analyzer_agent import basic_analysis

# Categorías válidas para validación
VALID_CATEGORIES = {"grammar", "vocabulary", "phrasal_verb", "expression", "collocation", "context_appropriateness"}

def get_user_plan_type(user_id: UUID) -> str:
    """Obtiene el tipo de plan del usuario desde la base de datos"""
    try:
        response = (
            supabase
            .table("users_profile")
            .select("subscription_type")
            .eq("id", str(user_id))
            .single()
            .execute()
        )
        
        if response.data:
            plan = response.data.get("subscription_type", "basic") or response.data.get("plan_type", "basic")
            return plan.lower()
        
        return "basic"
        
    except Exception as e:
        print(f"⚠️ Error getting user plan: {e}")
        return "basic"

def get_system_message_from_chat(chat_id: UUID) -> str:
    """Obtiene el system message de un chat específico"""
    try:
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
        
        chat_response = (
            supabase
            .table("chats")
            .select("context, role")
            .eq("id", str(chat_id))
            .single()
            .execute()
        )
        
        if chat_response.data:
            return chat_response.data.get("context", "") or f"You are a {chat_response.data.get('role', 'helpful')} English conversation partner."
        
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
    Ejecuta el análisis usando solo el basic analyzer
    """
    try:
        print(f"🔍 Analyzing message for user {user_id}")
        print(f"📝 User text: {user_text}")
        
        # Usar solo basic analyzer por ahora
        print("🔧 Executing BASIC analysis")
        analysis_result = basic_analysis(ai_text, user_text)
        analysis_result["plan_type"] = "basic"
        
        print(f"✅ Analysis complete: {len(analysis_result.get('feedback', []))} suggestions found")
        return analysis_result
        
    except Exception as e:
        print(f"❌ Error in analyze_message_by_plan: {e}")
        # Fallback mínimo
        return {
            "feedback": [],
            "prioritized": {"high": [], "medium": [], "low": []},
            "is_transcribed": False,
            "total_issues": 0,
            "summary": "Error en el análisis",
            "plan_type": "basic_fallback"
        }

def save_analysis(message_id: UUID, entries: List[Dict]) -> None:
    """Guarda análisis de un mensaje, filtrando entradas inválidas"""
    if not entries:
        print(f"✅ No analysis entries to save for message {message_id}")
        return

    valid_entries = []
    for entry in entries:
        # Adaptar formato del basic analyzer
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
            print(f"⚠️ Skipping invalid entry: {entry}")
            continue
            
        # Filtrar respuestas "no errors"
        if (
            mistake in ["", "EMPTY", "No errors found"] 
            or category == "none"
            or "no se encontraron errores" in explanation.lower()
        ):
            print(f"⚠️ Skipping 'no errors' entry")
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
    """Obtiene análisis siguiendo la relación correcta chat → mensajes → análisis"""
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
    """Detecta palabras del diccionario del usuario que fueron usadas en el chat"""
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

def calculate_chat_stats(analysis_points: List[MessageAnalysis]) -> Dict:
    """Calcula estadísticas del chat"""
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
    """Función de debug para verificar qué datos existen"""
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