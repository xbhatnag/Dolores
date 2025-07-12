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

from playwright.sync_api import sync_playwright
from playwright.sync_api import ViewportSize
from playwright.sync_api import Page

import qrcode
import io


def take_screenshot(page: Page, url: str, filename: str) -> bytes:
    while True:
        try:
            page.goto(url)
            return page.screenshot()
        except:
            # Give it another go in a few seconds
            time.sleep(10)
            pass


def create_qr_code(url: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    byte_stream = io.BytesIO()
    image.save(byte_stream, format="PNG")
    return byte_stream.getvalue()


@dataclasses.dataclass
class WrittenContent:
    source: str
    title: str
    type: str
    author: str
    tags: List[str]
    data: str
    url: str
    _pub_date: str

    def __getattr__(self, name):
        if name == "pub_date":
            return datetime.fromisoformat(self._pub_date)
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

    def published_after(self, cmp_date: datetime) -> bool:
        return self.pub_date > cmp_date


def strip_html(html: str) -> str:
    # Remove HTML tags and decode HTML entities
    soup = bs4.BeautifulSoup(html, features="html.parser")
    text = soup.get_text()
    return text.strip()


def normalize_date(date: str) -> str:
    return parse_date(date).astimezone(timezone.utc).isoformat()


def randomize_written_content_type_str() -> str:
    random.choice(["article", "piece", "story"])


def read_the_verge_long_form() -> List[WrittenContent]:
    feed = feedparser.parse("https://www.theverge.com/rss/index.xml")
    written_content = []
    for entry in feed.entries:
        written_content.append(
            WrittenContent(
                source="The Verge",
                title=strip_html(entry.title),
                tags=[t.get("term") for t in entry.tags],
                type=randomize_written_content_type_str(),
                author=entry.author,
                data=strip_html(entry.content[0].value),
                url=entry.link,
                _pub_date=normalize_date(entry.published),
            )
        )
    return written_content


def read_the_verge_quick_posts() -> List[WrittenContent]:
    feed = feedparser.parse("https://www.theverge.com/rss/quickposts")
    written_content = []
    for entry in feed.entries:
        written_content.append(
            WrittenContent(
                source="The Verge",
                title=strip_html(entry.title),
                tags=[t.get("term") for t in entry.tags],
                type="short post",
                author=entry.author,
                data=strip_html(entry.content[0].value),
                url=entry.link,
                _pub_date=normalize_date(entry.published),
            )
        )
    return written_content


def read_ars_technica() -> List[WrittenContent]:
    feed = feedparser.parse("https://feeds.arstechnica.com/arstechnica/index")
    written_content = []
    for entry in feed.entries:
        data = (
            strip_html(entry.content[0].value)
            .removesuffix("Comments")
            .strip()
            .removesuffix("Read full article")
            .strip()
        )
        written_content.append(
            WrittenContent(
                source="Ars Technica",
                title=entry.title,
                type=randomize_written_content_type_str(),
                tags=[t.get("term") for t in entry.tags],
                author=entry.author,
                data=data,
                url=entry.link.strip(),
                _pub_date=normalize_date(entry.published),
            )
        )
    return written_content


def read_hackaday() -> List[WrittenContent]:
    feed = feedparser.parse("https://hackaday.com/blog/feed/")
    written_content = []
    for entry in feed.entries:
        written_content.append(
            WrittenContent(
                source="Hack A Day",
                title=entry.title,
                type=randomize_written_content_type_str(),
                tags=[t.get("term") for t in entry.tags],
                author=entry.author,
                data=strip_html(entry.content[0].value),
                url=entry.link.strip(),
                _pub_date=normalize_date(entry.published),
            )
        )
    return written_content


def read_daring_fireball() -> List[WrittenContent]:
    feed = feedparser.parse("https://daringfireball.net/feeds/main")
    written_content = []
    for entry in feed.entries:
        # We want Gruber's pieces, not others'
        if "sponsors" in entry.id or "linked" in entry.id:
            continue

        title = getattr(entry, "title", "")

        # What in god's name is this?
        if not title:
            continue

        # He does this sometimes
        title = title.removeprefix("★ ")

        written_content.append(
            WrittenContent(
                source="Daring Fireball",
                title=title,
                type=randomize_written_content_type_str(),
                tags=[],
                author=entry.author,
                data=strip_html(entry.content[0].value),
                url=entry.link.strip(),
                _pub_date=normalize_date(entry.published),
            )
        )
    return written_content


def read_content_from_rss(after: datetime) -> List[WrittenContent]:
    the_verge_long_form = read_the_verge_long_form()
    the_verge_quick_posts = read_the_verge_quick_posts()
    ars_technica = read_ars_technica()
    hack_a_day = read_hackaday()
    daring_fireball = read_daring_fireball()

    # Put em all together
    all_written_content = (
        hack_a_day
        + the_verge_quick_posts
        + the_verge_long_form
        + ars_technica
        + daring_fireball
    )

    all_written_content = list(
        filter(lambda a: a.published_after(after), all_written_content)
    )
    all_written_content.sort(key=lambda a: a.pub_date, reverse=True)

    return all_written_content


def create_script(
    tts_client: texttospeech.TextToSpeechClient,
    chat: genai.chats.Chat,
    content: WrittenContent,
    filename: str,
    intros: list[str],
    credits: list[str],
    outros: list[str],
    page: Page,
):
    logging.info("Creating new script!")

    # Pick a voice for the TTS
    voice = choose_random_voice()

    # Determine if we want an intro and an outro
    want_intro = random.random() < 0.4
    want_outro = random.random() < 0.6

    # Ask Gemini to write the script
    prompt = ""

    if want_intro:
        intro_sample = random.choice(intros)
        prompt += '\nIntro Sample: "' + intro_sample + '"'
    credit_sample = random.choice(credits)
    prompt += '\nCredit Sample: "' + credit_sample + '"'
    if want_outro:
        intro_sample = random.choice(outros)
        prompt += '\nOutro Sample: "' + intro_sample + '"'

    prompt += f"""Source: {content.source}
Title: {content.title}
Content Type: {content.type}
Author: {content.author}"""

    if content.tags:
        prompt += f"\nTags: {','.join(content.tags)}"

    prompt += f"\nContent: {content.data}" ""

    response = chat.send_message(
        message=prompt,
    )

    # Now generate audio for it
    script_text: str = response.text.strip().replace("\n", " ")

    # Punctuate the end so the audio doesn't sound weird.
    if not script_text.endswith("."):
        script_text += "."

    audio = generate_audio(tts_client, script_text, filename, voice)

    # Get a screenshot of the page
    hero = take_screenshot(page, content.url, filename)

    # Generate a QRCode for the URL
    qr_code = create_qr_code(content.url)

    return Script(
        title=f"[{content.source}] {content.title}",
        description=script_text,
        hero=hero,
        audio=audio,
        qr_code=qr_code,
        footer_1=f"Written by {content.author}",
        footer_2=content.pub_date.strftime("%a, %d %b %Y, %I:%M:%S %p"),
        narrator=voice
    )


def research_loop(queue: Queue, after: datetime):
    logging.info("Reading prompts...")
    with open("./journalist/system_prompt.md") as f:
        system_prompt = f.read()

    with open("./journalist/intros.txt") as f:
        intros = f.read().splitlines()

    with open("./journalist/credits.txt") as f:
        credits = f.read().splitlines()

    with open("./journalist/outros.txt") as f:
        outros = f.read().splitlines()

    tts = texttospeech.TextToSpeechClient()
    tools = []
    # tools.append(types.Tool(url_context=types.UrlContext))
    # tools.append(types.Tool(google_search=types.GoogleSearch))
    chat = genai.Client(
        vertexai=True,
        project="dolores-cb057",
        location="us-west1",
        http_options=genai.types.HttpOptions(api_version="v1"),
    ).chats.create(
        model="gemini-2.5-pro",
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt, tools=tools
        ),
    )

    count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=ViewportSize(width=1920, height=1080))

        while True:
            logging.info("Getting written_content after %s", after)

            # Get all content from RSS feeds
            new_content = read_content_from_rss(after=after)

            # TODO: Ask Gemini to build context around the written_content
            logging.info("%d new written content read!", len(new_content))

            if new_content:
                # Set the next date to the most recent written_content
                after = new_content[0].pub_date

                # Create scripts for the content
                for content in new_content:
                    script = create_script(
                        tts,
                        chat,
                        content,
                        f"{count}_written_content",
                        intros,
                        credits,
                        outros,
                        page,
                    )
                    queue.put(script)
                    count += 1

            # Take it slow
            logging.info("Researcher is taking a 5 minute break...")
            time.sleep(60 * 5)
