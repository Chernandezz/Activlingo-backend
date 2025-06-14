# services/analysis_service.py - CORREGIDO PARA LA ESTRUCTURA REAL
from config.supabase_client import supabase
from schemas.chat_analysis import MessageAnalysis, LanguageAnalysisPoint
from uuid import UUID
import json

# Categorías válidas para validación
VALID_CATEGORIES = {"grammar", "vocabulary", "phrasal_verb", "expression", "collocation"}

def save_analysis(message_id: UUID, entries: list[dict]) -> None:
    """
    Guarda análisis de un mensaje, filtrando entradas inválidas
    """
    if not entries:
        return

    valid_entries = []
    for entry in entries:
        # Validar campos requeridos
        if not all([
            entry.get('mistake', '').strip(),
            entry.get('suggestion', '').strip(), 
            entry.get('explanation', '').strip(),
            entry.get('category') in VALID_CATEGORIES
        ]):
            continue
            
        # Filtrar "no errors" responses
        if (
            entry.get('mistake') in ["", "EMPTY", "No errors found"] 
            or entry.get('category') == "none"
            or "no se encontraron errores" in entry.get('explanation', '').lower()
        ):
            continue

        valid_entries.append({
            "message_id": str(message_id),
            "category": entry.get("category"),
            "mistake": entry.get("mistake").strip(),
            "issue": entry.get("issue", "").strip(),
            "suggestion": entry.get("suggestion").strip(),
            "explanation": entry.get("explanation").strip()
        })

    if not valid_entries:
        print(f"✅ No valid analysis entries for message {message_id}")
        return

    try:
        result = supabase.table("message_analysis").insert(valid_entries).execute()
        print(f"✅ Saved {len(valid_entries)} analysis entries for message {message_id}")
    except Exception as e:
        print(f"⚠️ Error saving analysis entries: {e}")
        for failed in valid_entries:
            print(f"❌ Failed entry: {failed}")


def get_analysis_by_chat_id(chat_id: UUID) -> list[MessageAnalysis]:
    """
    🔧 CORREGIDO: Obtiene análisis siguiendo la relación correcta chat → mensajes → análisis
    """
    try:
        # 1. Primero obtener todos los mensajes del chat
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
        
        # 2. Luego obtener todos los análisis para esos mensajes
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


def get_user_dictionary_words_in_chat(user_id: UUID, chat_id: UUID) -> list[dict]:
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
            .eq("sender", "human")  # 🔧 CORREGIDO: sender es "human", no "user"
            .execute()
        )
        
        if not messages_response.data:
            print(f"💬 No user messages found in chat {chat_id}")
            return []
        
        # 3. Extraer todas las palabras del chat
        chat_text = " ".join([msg["content"] for msg in messages_response.data])
        chat_words = set()
        
        # Limpiar y normalizar palabras
        for word in chat_text.split():
            clean_word = word.lower().strip(".,!?;:\"'()[]{}").strip()
            if len(clean_word) > 2:  # Solo palabras de 3+ caracteres
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


def process_ai_analysis_response(ai_response: str) -> list[dict]:
    """
    Procesa la respuesta del AI y la convierte en lista de diccionarios
    """
    try:
        # Limpiar la respuesta (remover markdown si existe)
        cleaned = ai_response.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # Parsear JSON
        analysis_data = json.loads(cleaned)
        
        # Asegurar que es una lista
        if not isinstance(analysis_data, list):
            print(f"⚠️ AI response is not a list: {type(analysis_data)}")
            return []
            
        return analysis_data
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing AI response as JSON: {e}")
        print(f"Raw response: {ai_response}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error processing AI response: {e}")
        return []


def calculate_chat_stats(analysis_points: list[MessageAnalysis]) -> dict:
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
    
    # Calcular score (100 - penalización por errores)
    total_errors = len(analysis_points)
    penalty_per_error = 3  # Menos penalización para ser más positivo
    overall_score = max(50, 100 - (total_errors * penalty_per_error))
    
    # Áreas de mejora (categorías con más errores)
    improvement_areas = sorted(
        category_counts.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:3]  # Top 3 áreas
    
    return {
        "total_errors": total_errors,
        "by_category": category_counts,
        "overall_score": overall_score,
        "improvement_areas": [area[0] for area in improvement_areas]
    }


def debug_chat_analysis(chat_id: UUID) -> dict:
    """
    🔍 Función de debug para verificar qué datos existen
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
        analysis_response = (
            supabase
            .table("message_analysis")
            .select("id, message_id, category, mistake")
            .in_("message_id", message_ids) if message_ids else []
            .execute()
        ) if message_ids else {"data": []}
        
        analysis = analysis_response.data or []
        
        return {
            "chat_exists": bool(chat_response.data),
            "messages_count": len(messages),
            "messages": messages[:5],  # Primeros 5 mensajes
            "analysis_count": len(analysis),
            "analysis": analysis[:5],  # Primeros 5 análisis
            "message_ids": message_ids
        }
        
    except Exception as e:
        return {"error": str(e)}