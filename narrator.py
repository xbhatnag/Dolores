import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import urllib3

from script import Script


def play_once(audio_file):
    subprocess.run(
        ["ffplay", "-v", "0", "-nodisp", "-autoexit", audio_file], check=True
    )


def play_once_and_delete(audio_file):
    play_once(audio_file)
    os.remove(audio_file)


def main():
    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Welcome to Jockey! I'm the Narrator.")

    while True:
        response = None
        while True:
            try:
                response = requests.get(f"http://localhost:8001/next")
                break
            except requests.exceptions.RequestException as e:
                logging.error("Failed to get articles. Waiting...")
                time.sleep(5)

        json_dict = response.json()
        script = Script(**json_dict)
        print(script.display_text)
        play_once("transition.mp3")
        play_once_and_delete(script.audio_file)


if __name__ == "__main__":
    main()
