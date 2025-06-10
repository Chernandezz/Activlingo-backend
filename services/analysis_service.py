from config.supabase_client import supabase
from schemas.chat_analysis import MessageAnalysis
from uuid import UUID

def save_analysis(message_id: UUID, entries: list[dict]) -> None:
    if not entries:
        return

    valid_entries = []
    for entry in entries:
        if (
            not entry.get('mistake') 
            or entry.get('mistake') in ["", "EMPTY"] 
            or entry.get('category') == "none"
        ):
            continue

        valid_entries.append({
            "message_id": str(message_id),
            "category": entry.get("category"),
            "mistake": entry.get("mistake"),
            "issue": entry.get("issue"),
            "suggestion": entry.get("suggestion"),
            "explanation": entry.get("explanation")
        })

    if not valid_entries:
        return

    try:
        supabase.table("message_analysis").insert(valid_entries).execute()
    except Exception as e:
        print("⚠️ Error saving multiple analysis entries:", e)
        for failed in valid_entries:
            print("❌ Failed entry:", failed)


def get_analysis_by_chat_id(chat_id: UUID) -> list[MessageAnalysis]:
    try:
        response = (
            supabase
            .table("message_analysis")
            .select("*, messages!inner(chat_id)")
            .eq("messages.chat_id", str(chat_id))
            .order("created_at", desc=False)
            .execute()
        )
        return [MessageAnalysis(**entry) for entry in response.data or []]
    except Exception as e:
        print("⚠️ Error fetching analysis:", e)
        return []
