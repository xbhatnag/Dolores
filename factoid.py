import dataclasses
import logging
import random
import threading
import time
from datetime import datetime, timezone
from queue import Queue
from typing import List

import bs4
import feedparser
from dateutil.parser import parse as parse_date
from google import genai
from google.cloud import texttospeech

from script import Script
from tts import choose_random_voice, generate_audio


def create_script(
    tts_client: texttospeech.TextToSpeechClient,
    chat: genai.chats.Chat,
    filename: str,
):
    # Pick a voice for the TTS
    voice = choose_random_voice()

    # Ask Gemini to write the script
    prompt = "Tell me another uncommon fun fact about technology!"

    response = chat.send_message(
        message=prompt,
    )
    audio_file = generate_audio(tts_client, response.text, filename, voice)

    print(response.text)

    return Script(display_text=response.text, audio_file=audio_file)


def factoid_loop(queue: Queue):
    tts = texttospeech.TextToSpeechClient()
    tools = []
    tools.append(genai.types.Tool(google_search=genai.types.GoogleSearch))
    chat = genai.Client(
        vertexai=True,
        project="dolores-cb057",
        location="us-west1",
        http_options=genai.types.HttpOptions(api_version="v1"),
    ).chats.create(
        model="gemini-2.5-pro",
        config=genai.types.GenerateContentConfig(
            tools=tools,
            system_instruction="""
Do not output anything except the fun fact.
You may start with an intro like: "Did you know ... " or "Here's something you may not know ..." or "Here's a fun fact ..."
""",
        ),
    )

    count = 0

    while True:
        logging.info("Getting new fun fact")

        script = create_script(tts, chat, f"{count}_fun_fact")
        queue.put(script)

        count += 1

        # Wait until we're running out of content
        logging.info("Factoid is taking a break...")
        time.sleep(120)


def spawn_factoid(queue: Queue) -> threading.Thread:
    logging.info("Spawning Factoid")
    thread = threading.Thread(target=factoid_loop, args=(queue,))
    thread.daemon = True
    thread.start()
    return thread
