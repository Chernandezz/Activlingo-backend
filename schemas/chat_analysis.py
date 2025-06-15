# schemas/chat_analysis.py - ACTUALIZADO CON CONTEXT_APPROPRIATENESS Y LEARNING_TIP
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID

class MessageAnalysis(BaseModel):
    id: UUID
    message_id: UUID
    category: Literal["grammar", "vocabulary", "phrasal_verb", "expression", "idiom", "collocation", "context_appropriateness", "none"]  # 🆕 AGREGADA context_appropriateness
    mistake: str
    issue: str
    suggestion: str
    explanation: str
    learning_tip: Optional[str] = None  # 🆕 AGREGADO learning_tip
    created_at: datetime

    class Config:
        from_attributes = True

# 🆕 ACTUALIZADO: Para el frontend TypeScript
class LanguageAnalysisPoint(BaseModel):
    """Modelo que coincide exactamente con el frontend"""
    id: str  # UUID como string para frontend
    chat_id: str  # Agregado para compatibilidad
    category: Literal["grammar", "vocabulary", "phrasal_verb", "expression", "idiom", "collocation", "context_appropriateness"]  # 🆕 AGREGADA context_appropriateness
    mistake: str
    suggestion: str
    explanation: str
    learning_tip: Optional[str] = None  # 🆕 AGREGADO learning_tip
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
            learning_tip=analysis.learning_tip,  # 🆕 INCLUIR learning_tip
            issue=analysis.issue,
            severity=cls._calculate_severity(analysis.category),
            created_at=analysis.created_at.isoformat()
        )
    
    @staticmethod
    def _calculate_severity(category: str) -> str:
        """Calcula severidad basada en categoría"""
        severity_map = {
            "grammar": "high",
            "vocabulary": "high",  # 🔄 CAMBIADO de medium a high
            "phrasal_verb": "medium",
            "expression": "low",
            "idiom": "low",
            "collocation": "medium",
            "context_appropriateness": "medium"  # 🆕 AGREGADA
        }
        return severity_map.get(category, "medium")