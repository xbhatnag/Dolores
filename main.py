import os
import time
import random
import json
from typing import List
import feedparser
import requests
from google import genai
from google.genai import types

from google.cloud import texttospeech
from subprocess import Popen, call
import bs4
import threading
from queue import SimpleQueue, Empty as QueueEmpty, LifoQueue
from dateutil.parser import parse as parse_date
import re
from pydantic import BaseModel
from datetime import datetime

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

def read_the_verge_long_form() -> List[Article]:
    feed = feedparser.parse('https://www.theverge.com/rss/index.xml')
    print(f"Got {len(feed.entries)} from The Verge - Long Form")
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

def read_the_verge_quick_posts() -> List[Article]:
    feed = feedparser.parse('https://www.theverge.com/rss/quickposts')
    print(f"Got {len(feed.entries)} from The Verge - Quick Posts")
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

def read_ars_technica() -> List[Article]:
    feed = feedparser.parse('https://feeds.arstechnica.com/arstechnica/index')
    print(f"Got {len(feed.entries)} from Ars Technica")
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content)
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

def read_hackaday() -> List[Article]:
    feed = feedparser.parse('https://hackaday.com/blog/feed/')
    print(f"Got {len(feed.entries)} from Hackaday")
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content)
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
    # Start a new script
    script = Script(article, voice)

    # Ask Gemini to write the script
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

    # Pick a voice for the TTS
    voice = random.choice(CHIRP3_VOICES)

    # Sometimes use the intro statement
    if flip_coin():
        intro_audio = generate_audio(tts_client, intro_text, f"{filename}_intro", script.voice)
        script.intro = ScriptPiece(intro_text, intro_audio)

    # Always use the formal part of the script
    formal_audio = generate_audio(tts_client, formal_text, f"{filename}_formal", script.voice)
    script.formal = ScriptPiece(formal_text, formal_audio)

    # Sometimes use the informal part of the script
    if flip_coin():
        informal_audio = generate_audio(tts_client, informal_text, f"{filename}_informal", script.voice)
        script.informal = ScriptPiece(informal_text, informal_audio)
    
    return script

def journalist_loop(to_process: SimpleQueue[Article]):
    last_modified: datetime = None

    def is_new_article(a: Article) -> bool:
        return last_modified and a.pub_date > last_modified

    while True:
        print("Running cycle...")
        the_verge_long_form = read_the_verge_long_form()
        the_verge_quick_posts = read_the_verge_quick_posts()
        ars_technica = read_ars_technica()
        hack_a_day = read_hackaday()

        # Put em all together
        articles = (hack_a_day + 
            the_verge_quick_posts +
            the_verge_long_form +
            ars_technica)
        
        # Sort by publishing date
        articles.sort(key=lambda a: a.pub_date)        

        # Add them to the queue for script writing
        for article in articles:
            if not is_new_article(article):
                print(f"{article.title} was already seen.")
                break
            
            # Otherwise process the article
            article.print()
            to_process.put(article)
        print("Cycle complete. Checking again in 60 seconds...")
        last_modified = datetime.now()
        time.sleep(60)

def script_writer_loop(articles: SimpleQueue[Article], scripts: SimpleQueue[Script]):
    tts_client = texttospeech.TextToSpeechClient()
    genai_client = genai.Client(
        vertexai=True,
        project='dolores-cb057',
        location='us-west1',
        http_options=types.HttpOptions(api_version="v1")
    )

    with open('system_prompt.md') as f:
        system_prompt = f.read()

    counter = 0

    while True:
        # Get the next article 
        article = articles.get()

        # Make a script
        script = create_script(tts_client, genai_client, article, f"{article.source}_{counter}", system_prompt)

        # Hand it to the news anchor for narrating
        scripts.put(script)

        # Move to the next article
        counter += 1

def news_anchor_loop(scripts: SimpleQueue[Script]):
    waiting_audio_process = None
    while True:
        try:
            # If an article is available right now,
            # transition to it immediately
            script = scripts.get_nowait()
            time.sleep(0.7)
            play_once('transition.mp3')
        except QueueEmpty:
            # Otherwise, play the longer "waiting music".
            # When an article comes in, stop the waiting
            # music and play the intro.
            waiting_audio_process = play_loop('waiting.mp3')
            script = scripts.get()
            waiting_audio_process.terminate()
            waiting_audio_process = None
            time.sleep(0.5)
            play_once('intro.mp3')

        # Finally play the entire script
        script.play()

def main():
    print("Welcome to Jockey!")
    articles: SimpleQueue[Article] = SimpleQueue()
    scripts: SimpleQueue[Script] = SimpleQueue()
    
    journalist_thread = threading.Thread(target=journalist_loop, args=(articles,))
    journalist_thread.daemon = True
    journalist_thread.start()

    while True:
        pass

    # writer_thread = threading.Thread(target=script_writer_loop, args=(articles, scripts,))
    # writer_thread.daemon = True
    # writer_thread.start()
    
    # news_anchor_loop(scripts)

if __name__ == "__main__":
    main()