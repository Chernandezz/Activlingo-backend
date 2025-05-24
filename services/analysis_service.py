from config.supabase_client import supabase
from schemas.chat_analysis import MessageAnalysis
from uuid import UUID  # Importante para tipado correcto


def save_analysis(message_id: UUID, entries: list[dict]) -> None:
    for entry in entries:
        if entry.get('mistake') in [None, "", "EMPTY"] or entry.get('category') == "none":
            continue
        try:
            supabase.table("message_analysis").insert({
                "message_id": str(message_id),  # Convertimos UUID a str para Supabase
                "category": entry["category"],
                "mistake": entry["mistake"],
                "issue": entry["issue"],
                "suggestion": entry["suggestion"],
                "explanation": entry["explanation"]
            }).execute()
        except Exception as e:
            print("⚠️ Error saving analysis:", e)


def get_analysis_by_chat_id(chat_id: UUID) -> list[MessageAnalysis]:
    response = (
        supabase
        .table("message_analysis")
        .select("*, messages!inner(chat_id)")
        .eq("messages.chat_id", str(chat_id))  # UUID → str
        .order("created_at", desc=False)
        .execute()
    )

    return [MessageAnalysis(**entry) for entry in response.data or []]
