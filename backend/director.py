import argparse
import base64
import io
import json
import logging
from datetime import datetime, timedelta
from queue import Queue
from zoneinfo import ZoneInfo

import qrcode
import qrcode.constants
from dateutil.parser import parse as parse_date
from flask import Flask
from google.cloud import texttospeech

from factoid import spawn_factoid
from xkcd import spawn_xkcd
from journalist import spawn_journalist
from script import Script
from tts import random_narrator, generate_audio


def create_qr_code(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    byte_stream = io.BytesIO()
    image.save(byte_stream, format="PNG")
    return byte_stream.getvalue()


tts = texttospeech.TextToSpeechClient()
queue: Queue = Queue()
app = Flask(__name__)


@app.route("/next")
def get_next_script():
    logging.info("Narrator is waiting for next script...")
    script: Script = queue.get()

    assert script.title
    assert script.audio

    narrator = random_narrator()
    audio_mp3 = generate_audio(tts, script.audio, narrator)
    b64_audio = base64.b64encode(audio_mp3).decode("ascii")

    b64_hero = base64.b64encode(script.hero).decode("ascii")

    b64_qr_code = ""
    if script.qr_code:
        qr_code_image = create_qr_code(script.qr_code)
        b64_qr_code = base64.b64encode(qr_code_image).decode("ascii")

    json_data = {
        "title": script.title,
        "description": script.description,
        "audio": b64_audio,
        "hero": b64_hero,
        "qr_code": b64_qr_code,
        "footer_1": script.footer_1,
        "footer_2": script.footer_2,
        "narrator": narrator,
    }
    return json_data


def now() -> datetime: 
    # We know we are in west coast.
    return datetime.now(tz=ZoneInfo("America/Los_Angeles"))


def main():
    global queue

    parser = argparse.ArgumentParser(description="Director")
    parser.add_argument(
        "--after", "-a", type=str, help="Only get articles after this date + time"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=8080, help="Port number for HTTP server"
    )
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Welcome to Jockey! I'm the Director.")

    after = now() - timedelta(days=1)
    if args.after:
        after = parse_date(args.after)

    spawn_journalist(queue, after)
    spawn_xkcd(queue)
    spawn_factoid(queue)

    # spawn_trendy(queue)

    # Serve HTTP server
    app.run(host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
