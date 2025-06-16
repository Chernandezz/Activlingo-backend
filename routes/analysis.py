# routes/analysis.py - RUTAS CON SELECCIÓN DE PLAN
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from schemas.chat_analysis import MessageAnalysis, LanguageAnalysisPoint
from services.analysis_service import (
    get_analysis_by_chat_id, 
    get_user_dictionary_words_in_chat,
    calculate_chat_stats,
    debug_chat_analysis,
    analyze_message_by_plan,
    get_user_plan_type,
    get_system_message_from_chat
)
from typing import List
from dependencies.auth import get_current_user
from pydantic import BaseModel

analysis_router = APIRouter()

# Modelo para el request de análisis en tiempo real
class AnalyzeRequest(BaseModel):
    chat_id: UUID
    ai_message: str
    user_message: str
    system_message: str = ""  # Opcional, se puede obtener del chat

@analysis_router.post("/analyze")
async def analyze_message_endpoint(
    request: AnalyzeRequest,
    user_id: UUID = Depends(get_current_user)
):
    """
    🌟 NUEVO: Analiza un mensaje usando el analizador apropiado según el plan del usuario
    """
    try:
        print(f"🔍 Analyzing message for user {user_id}")
        
        # Obtener system message si no viene en el request
        system_message = request.system_message
        if not system_message:
            system_message = get_system_message_from_chat(request.chat_id)
        
        # Ejecutar análisis según el plan del usuario
        analysis_result = await analyze_message_by_plan(
            user_id=user_id,
            system_message=system_message,
            ai_text=request.ai_message,
            user_text=request.user_message
        )
        
        return analysis_result
        
    except Exception as e:
        print(f"❌ Error in analyze endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing message: {str(e)}")

@analysis_router.get("/user/plan")
def get_user_plan_info(user_id: UUID = Depends(get_current_user)):
    """
    Obtiene información del plan del usuario
    """
    try:
        plan_type = get_user_plan_type(user_id)
        
        plan_features = {
            "basic": {
                "name": "Básico",
                "max_suggestions": 3,
                "features": ["Análisis básico", "Errores principales"],
                "analyzer_type": "single_agent"
            },
            "premium": {
                "name": "Premium", 
                "max_suggestions": 5,
                "features": [
                    "Análisis avanzado multi-agente",
                    "Sugerencias de contexto",
                    "Phrasal verbs especializados",
                    "Análisis de registro"
                ],
                "analyzer_type": "multi_agent"
            }
        }
        
        return {
            "current_plan": plan_type,
            "features": plan_features.get(plan_type, plan_features["basic"])
        }
        
    except Exception as e:
        print(f"❌ Error getting user plan: {e}")
        raise HTTPException(status_code=500, detail="Error fetching plan info")

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
        debug_info["user_plan"] = get_user_plan_type(user_id)
        return debug_info
    except Exception as e:
        return {"error": str(e)}

@analysis_router.get("/{chat_id}", response_model=List[LanguageAnalysisPoint])
def get_chat_analysis_by_chat(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    """
    Obtiene análisis siguiendo la estructura real
    """
    try:
        print(f"🔍 Getting analysis for chat {chat_id} (user: {user_id})")
        
        # Obtener análisis raw de la BD
        raw_analysis = get_analysis_by_chat_id(chat_id)
        print(f"📊 Found {len(raw_analysis)} raw analysis entries")
        
        # Filtrar análisis válidos
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
        
        # Agregar info del plan
        user_plan = get_user_plan_type(user_id)
        stats["user_plan"] = user_plan
        
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
        
        # Info del plan del usuario
        user_plan = get_user_plan_type(user_id)
        
        return {
            "analysis_points": frontend_points,
            "stats": stats,
            "dictionary_words_used": dictionary_words,
            "user_plan": user_plan,
            "summary": {
                "total_points": len(frontend_points),
                "score": stats["overall_score"],
                "dictionary_words_count": len(dictionary_words),
                "top_improvement_area": stats["improvement_areas"][0] if stats["improvement_areas"] else None,
                "plan_type": user_plan
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting chat summary for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching chat summary")