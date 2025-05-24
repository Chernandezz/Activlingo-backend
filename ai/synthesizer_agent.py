# ai/synthesizer_agent.py
from openai import OpenAI
import tempfile
import os

client = OpenAI()

def synthesize_speech(text: str) -> bytes:
    response = client.audio.speech.create(
        model="tts-1",  # o "tts-1-hd"
        voice="nova",   # voces: "nova", "shimmer", "echo"
        input=text,
        response_format="mp3"
    )
    return response.content
