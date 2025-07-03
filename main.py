import os
import time
import random
from typing import List, Optional
import feedparser
from google import genai
from google.genai import types

from google.cloud import texttospeech
from subprocess import Popen, call
import bs4
import threading
from queue import Empty as QueueEmpty, PriorityQueue
from dateutil.parser import parse as parse_date
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from functools import total_ordering

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

@total_ordering
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

    def __eq__(self, value):
        return isinstance(value, Article) and self.url == value.url
    
    def __lt__(self, value):
        return isinstance(value, Article) and self.pub_date < value.pub_date

@total_ordering
class Script:
    def __init__(self, article: Article, voice: str):
        self.article = article
        self.voice = voice
        self.script_text = None
        self.script_audio = None
    
    def print(self):
        print(f"-----------------------------------\n{self.article.title}\n{self.article.url}\n{self.article.pub_date}\nNarrated by {self.voice}\n\n{self.script_text}\n-----------------------------------\n")

    def play(self):
        play_once_and_delete(self.script_audio)
        time.sleep(1)

    def __eq__(self, value):
        return isinstance(value, Script) and self.article == value.article
    
    def __lt__(self, value):
        return isinstance(value, Script) and self.article < value.article

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
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.summary)
        if (num_words(content)) <= 30:
            # Quick post doesn't have enough content for AI to work with.
            # SKIP!
            print(f"Skipping small article from The Verge")
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
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content[0].value)
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
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content[0].value)
        articles.append(Article(
            source='Hack A Day',
            title=entry.title,
            author=entry.author,
            content=content,
            url=entry.link.strip(),
            pub_date=parse_date(entry.published)
        ))
    return articles

def read_daring_fireball() -> List[Article]:
    feed = feedparser.parse('https://daringfireball.net/feeds/main')
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content[0].value)
        
        # We want Gruber's pieces, not others'
        if "sponsors" in entry.id or "linked" in entry.id:
            continue

        articles.append(Article(
            source='Daring Fireball',
            title=getattr(entry, 'title', ''),
            author=entry.author,
            content=content,
            url=entry.link.strip(),
            pub_date=parse_date(entry.published)
        ))
    return articles


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

    # Start a new script
    script = Script(article, voice)

    # Determine if we want an intro and an outro
    want_intro = flip_coin(0.4)
    want_outro = flip_coin(0.6)

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
            system_instruction=system_prompt
        ),
        contents=prompt
    )

    # Always use the formal part of the script
    script.script_text = response.text
    script.script_audio = generate_audio(tts_client, script.script_text, filename, script.voice)
    
    return script

def today_utc() -> datetime:
    # We know we are in west coast.
    # Normalize it to UTC.
    return datetime.now(tz=ZoneInfo("America/Los_Angeles")).astimezone(timezone.utc)

def get_priority(article: Article) -> int:
    today = today_utc()
    diff = today - article.pub_date
    minutes = int(diff.total_seconds() / 60)
    return minutes

def journalist_loop(to_process: PriorityQueue):
    # When starting for the first time,
    # Don't include articles more than 3 days old
    last_checked = today_utc() - timedelta(days = 3)

    def is_new_article(a: Article) -> bool:
        # A new article would be one that is newer than the last time
        # we tried to pull articles.
        return (last_checked is None) or (a.pub_date > last_checked)

    while True:
        print("Running cycle...")
        the_verge_long_form = read_the_verge_long_form()
        the_verge_quick_posts = read_the_verge_quick_posts()
        ars_technica = read_ars_technica()
        hack_a_day = read_hackaday()
        daring_fireball = read_daring_fireball()

        # Put em all together
        articles = (hack_a_day + 
            the_verge_quick_posts +
            the_verge_long_form +
            ars_technica +
            daring_fireball)
        
        # Normalize all publishing dates to UTC
        for article in articles:
            article.pub_date = article.pub_date.astimezone(timezone.utc)
        
        # Sort by publishing date
        articles.sort(key=lambda a: a.pub_date, reverse=True)        

        # Add them to the queue for script writing
        count = 0
        for article in articles:
            if not is_new_article(article):
                print(f"{article.title} was already seen.")
                
                # If this article is already seen, then so are
                # the older ones.
                break
            
            # Otherwise process the article
            priority = get_priority(article)
            to_process.put((priority, article))
            count+=1

        # Set the last time we did a refresh.
        last_checked = today_utc()
        print(f"Added {count} articles. Checking again in 10 minutes...")
        time.sleep(60 * 10)

def script_writer_loop(articles: PriorityQueue, scripts: PriorityQueue):
    tts_client = texttospeech.TextToSpeechClient()
    genai_client = genai.Client(
        vertexai=True,
        project='dolores-cb057',
        location='us-west1',
        http_options=types.HttpOptions(api_version="v1")
    )

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
        # Get the next article 
        priority, article = articles.get()
        print(f"Script writer is moving to next article with priority {priority}")

        # Make a script
        script = create_script(tts_client, genai_client, article, f"{article.source}_{counter}", system_prompt, intros, credits, outros)

        # Hand it to the news anchor for narrating
        scripts.put((priority, script))

        # Move to the next article
        counter += 1

        while (scripts.qsize() > 4):
            # Take a break, you earned it
            print("Script writer is on break...")
            time.sleep(30)

def news_anchor_loop(scripts: PriorityQueue):
    waiting_audio_process = None
    while True:
        try:
            # If an article is available right now,
            # transition to it immediately
            _, script = scripts.get_nowait()
            time.sleep(0.7)
            script.print()
            play_once('transition.mp3')
        except QueueEmpty:
            # Otherwise, play the longer "waiting music".
            # When an article comes in, stop the waiting
            # music and play the intro.
            waiting_audio_process = play_loop('waiting.mp3')
            _, script = scripts.get()
            waiting_audio_process.terminate()
            waiting_audio_process = None
            time.sleep(0.5)
            script.print()
            play_once('intro.mp3')

        # Finally play the entire script
        script.play()

def main():
    print("Welcome to Jockey!")
    articles = PriorityQueue()
    scripts = PriorityQueue()
    
    journalist_thread = threading.Thread(target=journalist_loop, args=(articles,))
    journalist_thread.daemon = True
    journalist_thread.start()

    writer_thread = threading.Thread(target=script_writer_loop, args=(articles, scripts,))
    writer_thread.daemon = True
    writer_thread.start()
    
    news_anchor_loop(scripts)

if __name__ == "__main__":
    main()