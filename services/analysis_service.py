from config.supabase_client import supabase

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
