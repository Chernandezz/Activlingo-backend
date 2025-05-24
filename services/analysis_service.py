from config.supabase_client import supabase
from schemas.chat_analysis import MessageAnalysis

def save_analysis(message_id: int, entries: list[dict]) -> None:
    for entry in entries:
        if entry.get('mistake') in [None, "", "EMPTY"] or entry.get('category') == "none":
            continue
        try:
            supabase.table("message_analysis").insert({
                "message_id": message_id,
                "category": entry["category"],
                "mistake": entry["mistake"],
                "issue": entry["issue"],
                "suggestion": entry["suggestion"],
                "explanation": entry["explanation"]
            }).execute()
        except Exception as e:
            print("⚠️ Error saving analysis:", e)



def get_analysis_by_chat_id(chat_id: int) -> list[MessageAnalysis]:
    response = supabase.table("message_analysis").select("*, messages!inner(chat_id)").eq("messages.chat_id", chat_id).order("created_at", desc=False).execute()

    return [MessageAnalysis(**entry) for entry in response.data or []]
