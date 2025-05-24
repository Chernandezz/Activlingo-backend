import tempfile
from openai import OpenAI
from fastapi import UploadFile
import os

client = OpenAI()

async def transcribe_audio_openai(file: UploadFile) -> str:
    # Guardar archivo temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # Usar Whisper de OpenAI
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="en"
            )
        return transcript
    finally:
        os.remove(tmp_path)
