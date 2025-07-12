import os
import subprocess
import time

import requests

from script import Script


def play_once(audio_file):
    subprocess.run(
        ["ffplay", "-v", "0", "-nodisp", "-autoexit", audio_file],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def play_once_and_delete(audio_file):
    play_once(audio_file)
    os.remove(audio_file)


def main():
    print("Welcome to Jockey! I'm the Narrator.")

    while True:
        response = None

        print("Waiting for new content to narrate...")
        while True:
            try:
                response = requests.get(f"http://localhost:8001/next")
                break
            except requests.exceptions.RequestException as e:
                print("Failed to get articles. Waiting for 60 seconds...")
                time.sleep(60)

        json_dict = response.json()
        script = Script(**json_dict)
        print("-----------------------------------------")
        print(script.display_text)
        print("-----------------------------------------")
        play_once("transition.mp3")
        play_once_and_delete(script.audio_file)


if __name__ == "__main__":
    main()
