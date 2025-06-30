import os
import time
import random
import json
import feedparser
import requests
from google import genai
from google.genai import types

from google.cloud import texttospeech
from subprocess import Popen, call
import bs4
import threading
from queue import SimpleQueue, Empty as QueueEmpty
from dateutil.parser import parse as parse_date
import re
from pydantic import BaseModel

# These are the good voices from Chirp3
CHIRP3_VOICES = [
    "Puck",
    "Achernar",
    "Laomedeia",
    "Achird",
    "Sadachbia",
]

def play_once(audio_file):
    call(['ffplay', '-v', '0', '-nodisp', '-autoexit', audio_file])

def play_loop(audio_file):
    return Popen(['ffplay', '-v', '0', '-nodisp', '-loop', '0', audio_file])

def play_once_and_delete(audio_file):
    play_once(audio_file)
    os.remove(audio_file)

def strip_html(html: str) -> str:
    # Remove HTML tags and decode HTML entities
    soup = bs4.BeautifulSoup(html, features="html.parser")
    text = soup.get_text()
    return text.strip()

def interleave_arrays(*arrays):
    # Interleave multiple lists
    result = []
    for group in zip(*arrays):
        result.extend(group)
    # Add leftovers
    for arr in arrays:
        result.extend(arr[len(arrays[0]):])
    return result

class Article:
    def __init__(self, source, title, author, content, url, pub_date):
        self.source = source
        self.title = title
        self.author = author
        self.content = content
        self.url = url
        self.pub_date = pub_date

    def print(self):
        print(f"-----------------------------------\n📰 {self.title}\n✍️ {self.author} @ {self.source}\n🌐 {self.url}\n📅 {self.pub_date}\n-----------------------------------")

class ScriptPiece:
    def __init__(self, text, audio_file):
        self.text = text
        self.audio_file = audio_file

class Script:
    def __init__(self, article: Article, voice: str):
        self.article = article
        self.voice = voice
        self.intro = None
        self.formal = None
        self.informal = None

    def play(self):
        script_text = f"-----------------------------------\n🗣️ Narrated by {self.voice}\n\n"
        if self.intro:
            script_text += self.intro.text + '\n\n'
        script_text += self.formal.text
        if self.informal:
            script_text += '\n\n' + self.informal.text
        script_text += '\n-----------------------------------\n'
        print(script_text)

        if self.intro:
            play_once_and_delete(self.intro.audio_file)
            time.sleep(0.5)
        play_once_and_delete(self.formal.audio_file)
        if self.informal:
            time.sleep(0.7)
            play_once_and_delete(self.informal.audio_file)
        time.sleep(1)

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

def read_the_verge_long_form():
    feed = feedparser.parse('https://www.theverge.com/rss/index.xml')
    articles = []
    for entry in feed.entries:
        summary = entry.summary
        articles.append(Article(
            source='The Verge',
            title=strip_html(entry.title),
            author=entry.author,
            content=strip_html(summary),
            url=entry.link,
            pub_date=parse_date(entry.published)
        ))
    return articles

def num_words(input: str):
    return len(input.split())

def read_the_verge_quick_posts():
    feed = feedparser.parse('https://www.theverge.com/rss/quickposts')
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.summary)
        if (num_words(content)) <= 30:
            # Quick post doesn't have enough content for AI to work with.
            # SKIP!
            print(f"Skipping {content}")
            continue
        # TODO: Disable informal opinions for short content, not enough
        # data to work with.

        articles.append(Article(
            source='The Verge',
            title=strip_html(entry.title),
            author=entry.author,
            content=content,
            url=entry.link,
            pub_date=parse_date(entry.published)
        ))
    return articles

def read_ars_technica():
    feed = feedparser.parse('https://feeds.arstechnica.com/arstechnica/index')
    articles = []
    for entry in feed.entries:
        content = strip_html(getattr(entry, 'content', [{'value': ''}])[0]['value'])
        content = content.removesuffix('Comments').strip()
        content = content.removesuffix('Read full article').strip()
        articles.append(Article(
            source='Ars Technica',
            title=entry.title,
            author=entry.author,
            content=content,
            url=entry.link.strip(),
            pub_date=parse_date(entry.published)
        ))
    return articles

def read_hackaday():
    feed = feedparser.parse('https://hackaday.com/blog/feed/')
    articles = []
    for entry in feed.entries:
        content = strip_html(getattr(entry, 'content', [{'value': ''}])[0]['value'])
        articles.append(Article(
            source='Hack A Day',
            title=entry.title,
            author=entry.author,
            content=content,
            url=entry.link.strip(),
            pub_date=parse_date(entry.published)
        ))
    return articles

def flip_coin(odds=0.5):
    return random.random() < odds

class GeneratedScript(BaseModel):
    intro: str
    formal: str
    informal: str

def create_script(
        tts_client: texttospeech.TextToSpeechClient,
        genai_client: genai.Client,
        article: Article,
        filename: str,
        system_prompt: str,
):
    voice = random.choice(CHIRP3_VOICES)
    script = Script(article, voice)

    prompt = f"""Move onto this article:

News Organization: {article.source}
Title: {article.title}
Author: {article.author}
Content: {article.content}"""
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=GeneratedScript
        ),
        contents=prompt,
    )

    intro_text = response.parsed.intro
    formal_text = response.parsed.formal
    informal_text = response.parsed.informal

    if flip_coin():
        intro_audio = generate_audio(tts_client, intro_text, f"{filename}_intro", script.voice)
        script.intro = ScriptPiece(intro_text, intro_audio)

    formal_audio = generate_audio(tts_client, formal_text, f"{filename}_formal", script.voice)
    script.formal = ScriptPiece(formal_text, formal_audio)
    if flip_coin():
        informal_audio = generate_audio(tts_client, informal_text, f"{filename}_informal", script.voice)
        script.informal = ScriptPiece(informal_text, informal_audio)
    
    return script

def script_writer_loop(scripts: SimpleQueue[Script]):
    the_verge_long_form = read_the_verge_long_form()
    the_verge_quick_posts = read_the_verge_quick_posts()
    ars_technica = read_ars_technica()
    hack_a_day = read_hackaday()
    articles = interleave_arrays(
        hack_a_day,
        the_verge_quick_posts,
        the_verge_long_form,
        ars_technica
    )

    for article in articles:
        article.print()

    tts_client = texttospeech.TextToSpeechClient()
    genai_client = genai.Client(
        vertexai=True,
        project='dolores-cb057',
        location='us-west1',
        http_options=types.HttpOptions(api_version="v1")
    )

    with open('system_prompt.md') as f:
        system_prompt = f.read()

    for idx, article in enumerate(articles):
        script = create_script(tts_client, genai_client, article, f"{article.source}_{idx}", system_prompt)
        scripts.put(script)

def news_anchor_loop(scripts: SimpleQueue[Script]):
    waiting_audio_process = None
    while True:
        try:
            script = scripts.get_nowait()
            time.sleep(0.7)
            play_once('transition.mp3')
        except QueueEmpty:
            waiting_audio_process = play_loop('waiting.mp3')
            script = scripts.get()
            waiting_audio_process.terminate()
            waiting_audio_process = None
            time.sleep(0.5)
            play_once('intro.mp3')
        script.play()

def main():
    print("Welcome to Jockey!")
    scripts: SimpleQueue[Script] = SimpleQueue()
    writer_thread = threading.Thread(target=script_writer_loop, args=(scripts,))
    writer_thread.daemon = True
    writer_thread.start()
    news_anchor_loop(scripts)

if __name__ == "__main__":
    main()