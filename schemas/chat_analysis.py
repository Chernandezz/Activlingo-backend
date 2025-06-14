# schemas/chat_analysis.py - ACTUALIZADO
from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from uuid import UUID

class MessageAnalysis(BaseModel):
    id: UUID
    message_id: UUID
    category: Literal["grammar", "vocabulary", "phrasal_verb", "expression", "idiom", "collocation", "none"]  # 🔧 Específico
    mistake: str
    issue: str
    suggestion: str
    explanation: str
    created_at: datetime

    class Config:
        from_attributes = True

# 🆕 NUEVO: Para el frontend TypeScript
class LanguageAnalysisPoint(BaseModel):
    """Modelo que coincide exactamente con el frontend"""
    id: str  # UUID como string para frontend
    chat_id: str  # Agregado para compatibilidad
    category: Literal["grammar", "vocabulary", "phrasal_verb", "expression", "idiom", "collocation"]
    mistake: str
    suggestion: str
    explanation: str
    issue: str | None = None  # Opcional
    severity: Literal["low", "medium", "high"] = "medium"  # Nuevo campo
    created_at: str  # ISO string para frontend

    @classmethod
    def from_message_analysis(cls, analysis: MessageAnalysis, chat_id: UUID):
        """Convierte MessageAnalysis a LanguageAnalysisPoint"""
        return cls(
            id=str(analysis.id),
            chat_id=str(chat_id),
            category=analysis.category,
            mistake=analysis.mistake,
            suggestion=analysis.suggestion,
            explanation=analysis.explanation,
            issue=analysis.issue,
            severity=cls._calculate_severity(analysis.category),
            created_at=analysis.created_at.isoformat()
        )
    
    @staticmethod
    def _calculate_severity(category: str) -> str:
        """Calcula severidad basada en categoría"""
        severity_map = {
            "grammar": "high",
            "vocabulary": "medium", 
            "phrasal_verb": "medium",
            "expression": "low",
            "idiom": "low",
            "collocation": "medium"
        }
        return severity_map.get(category, "medium")