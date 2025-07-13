import logging
import threading
import time
from queue import Queue

from google import genai
from google.cloud import texttospeech

from script import Script


def create_script(
    chat: genai.chats.Chat,
):

    # Ask Gemini to write the script
    prompt = "Tell me another uncommon fun fact about consumer technology!"

    fact = (
        chat.send_message(
            message=prompt,
        )
        .text.strip()
        .replace("\n", " ")
    )

    return Script(
        title="Fun Fact!",
        description=fact,
        audio=fact,
        hero=bytes(),
        qr_code="",
        footer_1="",
        footer_2="",
    )


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

        script = create_script(chat)
        queue.put(script)

        count += 1

        # Wait until we're running out of content
        logging.info("Factoid is taking a 30 minute break...")
        time.sleep(60)


def spawn_factoid(queue: Queue) -> threading.Thread:
    logging.info("Spawning Factoid")
    thread = threading.Thread(target=factoid_loop, args=(queue,))
    thread.daemon = True
    thread.start()
    return thread
