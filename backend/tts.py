import logging
import random

from google.cloud import texttospeech


def random_narrator() -> str:
    # These are the good voices from Chirp3
    return random.choice(
        [
            "Puck",
            "Achernar",
            "Laomedeia",
            "Achird",
            "Sadachbia",
        ]
    )


def generate_audio(
    tts_client: texttospeech.TextToSpeechClient, text: str, voice: str
) -> bytes:
    logging.info("Generating audio from script...")
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code="en-US", name=f"en-US-Chirp3-HD-{voice}"
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1.1
    )
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice_params, audio_config=audio_config
    )
    return response.audio_content
