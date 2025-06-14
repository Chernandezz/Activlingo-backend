# routers/analysis.py - CON DEBUG PARA VERIFICAR DATOS
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from schemas.chat_analysis import MessageAnalysis, LanguageAnalysisPoint
from services.analysis_service import (
    get_analysis_by_chat_id, 
    get_user_dictionary_words_in_chat,
    calculate_chat_stats,
    debug_chat_analysis  # 🔍 Nueva función de debug
)
from typing import List
from dependencies.auth import get_current_user

analysis_router = APIRouter()

@analysis_router.get("/{chat_id}/debug")
def debug_chat_data(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    """
    🔍 ENDPOINT DE DEBUG: Ver qué datos existen realmente
    """
    try:
        debug_info = debug_chat_analysis(chat_id)
        return debug_info
    except Exception as e:
        return {"error": str(e)}

@analysis_router.get("/{chat_id}", response_model=List[LanguageAnalysisPoint])
def get_chat_analysis_by_chat(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    """
    🔧 CORREGIDO: Obtiene análisis siguiendo la estructura real
    """
    try:
        print(f"🔍 Getting analysis for chat {chat_id} (user: {user_id})")
        
        # Obtener análisis raw de la BD
        raw_analysis = get_analysis_by_chat_id(chat_id)
        print(f"📊 Found {len(raw_analysis)} raw analysis entries")
        
        # Filtrar análisis válidos (sin errores vacíos)
        valid_analysis = [
            analysis for analysis in raw_analysis 
            if analysis.category != "none" and analysis.mistake.strip()
        ]
        print(f"✅ {len(valid_analysis)} valid analysis entries after filtering")
        
        # Convertir a formato frontend
        frontend_points = [
            LanguageAnalysisPoint.from_message_analysis(analysis, chat_id)
            for analysis in valid_analysis
        ]
        
        return frontend_points
        
    except Exception as e:
        print(f"❌ Error getting analysis for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching analysis: {str(e)}")


@analysis_router.get("/{chat_id}/stats")
def get_chat_stats(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    """
    Estadísticas del chat para el score y métricas
    """
    try:
        analysis = get_analysis_by_chat_id(chat_id)
        stats = calculate_chat_stats(analysis)
        
        return stats
        
    except Exception as e:
        print(f"❌ Error getting stats for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching stats")


@analysis_router.get("/{chat_id}/dictionary-words")
def get_dictionary_words_used(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    """
    Palabras del diccionario del usuario que fueron usadas en el chat
    """
    try:
        used_words = get_user_dictionary_words_in_chat(user_id, chat_id)
        
        return {
            "words_used": used_words,
            "total_count": len(used_words)
        }
        
    except Exception as e:
        print(f"❌ Error getting dictionary words for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching dictionary words")


@analysis_router.get("/{chat_id}/summary")
def get_chat_analysis_summary(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    """
    Resumen completo del análisis del chat
    """
    try:
        # Obtener análisis
        raw_analysis = get_analysis_by_chat_id(chat_id)
        valid_analysis = [
            analysis for analysis in raw_analysis 
            if analysis.category != "none" and analysis.mistake.strip()
        ]
        
        # Obtener estadísticas
        stats = calculate_chat_stats(valid_analysis)
        
        # Obtener palabras del diccionario usadas
        dictionary_words = get_user_dictionary_words_in_chat(user_id, chat_id)
        
        # Convertir análisis a formato frontend
        frontend_points = [
            LanguageAnalysisPoint.from_message_analysis(analysis, chat_id)
            for analysis in valid_analysis
        ]
        
        return {
            "analysis_points": frontend_points,
            "stats": stats,
            "dictionary_words_used": dictionary_words,
            "summary": {
                "total_points": len(frontend_points),
                "score": stats["overall_score"],
                "dictionary_words_count": len(dictionary_words),
                "top_improvement_area": stats["improvement_areas"][0] if stats["improvement_areas"] else None
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting chat summary for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching chat summary")