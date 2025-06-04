from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List
from uuid import UUID
from io import BytesIO
from schemas.message import Message, MessageCreate, MessageResponse
from services.message_service import create_message, get_messages, delete_message, handle_human_message
from ai.transcriber_agent import transcribe_audio_openai
from ai.synthesizer_agent import synthesize_speech
from pydantic import BaseModel

message_router = APIRouter()


@message_router.get("/", response_model=List[Message])
def list_messages(chat_id: UUID = Query(...)):
    return get_messages(chat_id)


@message_router.post("/", response_model=MessageResponse)
def create(msg: MessageCreate):
    created = handle_human_message(msg)
    if not created:
        raise HTTPException(status_code=500, detail="Error creating message")
    return created


@message_router.delete("/{message_id}")
def delete(message_id: UUID):
    success = delete_message(message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or already deleted")
    return {"success": True, "message": "Message deleted successfully"}


@message_router.post("/transcribe-audio/")
async def transcribe_audio(
    file: UploadFile = File(...),
    chat_id: UUID = Query(...),
    user_id: UUID = Form(...)
) -> dict:
    # 1) Obtener la transcripción del archivo de audio
    transcription = await transcribe_audio_openai(file)

    # 2) Crear el mensaje humano
    msg = MessageCreate(
        chat_id=chat_id,
        sender="human",
        content=transcription,
        user_id=user_id
    )

    # 3) Procesar el mensaje humano, devolviendo IA + tareas completadas
    response = handle_human_message(msg)

    if not response:
        raise HTTPException(status_code=500, detail="AI failed to respond")

    # 4) Retornar transcripción, respuesta IA y tareas completadas
    return {
        "user_text": transcription,
        "ai_text": response["message"].content,
        "completed_tasks": response.get("completed_tasks", [])
    }


class SpeakRequest(BaseModel):
    text: str


@message_router.post("/speak")
def speak_text(body: SpeakRequest):
    audio_bytes = synthesize_speech(body.text)
    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/mpeg"
    )
