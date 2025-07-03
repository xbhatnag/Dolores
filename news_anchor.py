import time
from jockey_types import Script
from jockey_sockets import *
import socket
import struct
import logging
import subprocess
import os

def play_once(audio_file):
    subprocess.run(['ffplay', '-v', '0', '-nodisp', '-autoexit', audio_file], check=True)

def play_once_and_delete(audio_file):
    play_once(audio_file)
    os.remove(audio_file)

def main():
    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Welcome to Jockey! I'm the News Anchor.")
    logging.info("Connecting to Script Writer...")

    script_writer = connect_to_socket("jockey_script_writer")

    while True:
        logging.info("Waiting for next script...")
        script: Script = receive_object(Script, script_writer)
        time.sleep(0.7)

        output = f"""URL: {script.article.url}
Title: {script.article.title}
Source: {script.article.source}
Date: {script.article.pub_date}
Author: {script.article.author}
Voice: {script.voice}

{script.script_text}
"""

        print(output)
        play_once('transition.mp3')
        play_once_and_delete(script.script_audio)

if __name__ == "__main__":
    main()