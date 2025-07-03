import time
import random
from google import genai
from google.genai import types

from google.cloud import texttospeech
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from jockey_types import Article, Script
import socket
import struct
import logging
from jockey_sockets import *

# These are the good voices from Chirp3
CHIRP3_VOICES = [
    "Puck",
    "Achernar",
    "Laomedeia",
    "Achird",
    "Sadachbia",
]

def generate_audio(tts_client: texttospeech.TextToSpeechClient, text: str, filename: str, voice: str) -> str:
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=f"en-US-Chirp3-HD-{voice}"
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config
    )
    path = f"/dev/shm/{filename}.mp3"
    with open(path, "wb") as out:
        out.write(response.audio_content)
    return path

def flip_coin(odds=0.5):
    return random.random() < odds

def create_script(
        tts_client: texttospeech.TextToSpeechClient,
        genai_client: genai.Client,
        article: Article,
        filename: str,
        system_prompt: str,
        intros: list[str],
        credits: list[str],
        outros: list[str]
):
    # Pick a voice for the TTS
    voice = random.choice(CHIRP3_VOICES)

    # Determine if we want an intro and an outro
    want_intro = flip_coin(0.4)
    want_outro = flip_coin(0.6)

    tools = []
    # tools.append(types.Tool(url_context=types.UrlContext))
    # tools.append(types.Tool(google_search=types.GoogleSearch))

    # Ask Gemini to write the script
    prompt = ""

    if want_intro:
        intro_sample = random.choice(intros)
        prompt += "\nIntro Sample: \"" + intro_sample + "\""
    credit_sample = random.choice(credits)
    prompt += "\nCredit Sample: \"" + credit_sample + "\""
    if want_outro:
        intro_sample = random.choice(outros)
        prompt += "\nOutro Sample: \"" + intro_sample + "\""

    prompt += f"""
Article Source: {article.source}
Article Title: {article.title}
Article URL: {article.url}
Article Author: {article.author}
Article Content: {article.content}"""
    
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=tools
        ),
        contents=prompt,
    )

    # Always use the formal part of the script
    script_text = response.text
    script_audio = generate_audio(tts_client, script_text, filename, voice)
    
    return Script(article, voice, script_text, script_audio)

def today_utc() -> datetime:
    # We know we are in west coast.
    # Normalize it to UTC.
    return datetime.now(tz=ZoneInfo("America/Los_Angeles")).astimezone(timezone.utc)

def get_article(s: socket.socket) -> Article:
    data = s.recv(4)
    assert data, "Socket has disconnected"
    assert len(data) == 4, "Received less bytes than expected"

    length = struct.unpack('!I', data)[0]
    logging.debug(f"Reading {length} bytes...")
    
    data = s.recv(length)
    assert data, "Socket has disconnected"

    json_str = data.decode("utf-8")
    a = Article.from_json(json_str)
    logging.info("Received article: %s", a.title)
    return a

def main():
    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Welcome to Jockey! I'm the Script Writer.")

    logging.info("Connecting to Researcher...")
    researcher = connect_to_socket("jockey_researcher")

    logging.info("Waiting for news anchor to connect...")
    server_socket = create_server_socket("jockey_script_writer")
    news_anchor, addr = server_socket.accept()
    logging.info("New connection: %s", addr)

    logging.info("Setting up Google APIs...")
    tts_client = texttospeech.TextToSpeechClient()
    genai_client = genai.Client(
        vertexai=True,
        project='dolores-cb057',
        location='us-west1',
        http_options=types.HttpOptions(api_version="v1")
    )

    logging.info("Reading prompts...")
    with open('system_prompt.md') as f:
        system_prompt = f.read()

    with open('intros.txt') as f:
        intros = f.read().splitlines()
    
    with open('credits.txt') as f:
        credits = f.read().splitlines()

    with open('outros.txt') as f:
        outros = f.read().splitlines()

    counter = 0

    while True:
        logging.info("Waiting for next article...")

        article: Article = receive_object(Article, researcher)
        script = create_script(tts_client, genai_client, article, f"{article.source}_{counter}", system_prompt, intros, credits, outros)
        counter+=1

        logging.info("Script created: %s", script.script_audio)
        send_object(script, news_anchor)

if __name__ == "__main__":
    main()