import dataclasses
import io
import logging
import random
import time
from datetime import datetime, timezone
from queue import Queue
from typing import List

import bs4
import qrcode
import qrcode.constants
import requests
import xmltodict
from dateutil.parser import parse as parse_date
from google import genai
from google.cloud import texttospeech
from playwright.sync_api import Page, ViewportSize, sync_playwright

from script import Script
from tts import choose_random_voice, generate_audio


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
    authors: List[str]
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
    return random.choice(["article", "piece", "story"])


def get_authors(entry: dict) -> List[str]:
    if isinstance(entry["author"], list):
        return [author["name"] for author in entry["author"]]
    else:
        return [entry["author"]["name"]]

def get_xml(url: str) -> dict:
    response = requests.get(url)

    if response.status_code != 200:
        raise AssertionError("Failed to get RSS feed: %d", response.status_code)

    rss = xmltodict.parse(response.text)
    return rss

def read_the_verge_long_form() -> List[WrittenContent]:
    xml = get_xml("https://www.theverge.com/rss/index.xml")
    entries = xml["feed"]["entry"]
    written_content = []

    for entry in entries:
        written_content.append(
            WrittenContent(
                source="The Verge",
                title=strip_html(entry["title"]["#text"]),
                tags=[category["@term"] for category in entry["category"]],
                type=randomize_written_content_type_str(),
                authors=get_authors(entry),
                data=strip_html(entry["content"]["#text"]),
                url=entry["link"]["@href"],
                _pub_date=normalize_date(entry["published"]),
            )
        )

    return written_content


def read_the_verge_quick_posts() -> List[WrittenContent]:
    xml = get_xml("https://www.theverge.com/rss/quickposts")
    entries = xml["feed"]["entry"]
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="The Verge",
                title=strip_html(entry["title"]["#text"]),
                tags=[category["@term"] for category in entry["category"]],
                type=randomize_written_content_type_str(),
                authors=get_authors(entry),
                data=strip_html(entry["content"]["#text"]),
                url=entry["link"]["@href"],
                _pub_date=normalize_date(entry["published"]),
            )
        )
    return written_content


def read_ars_technica() -> List[WrittenContent]:
    xml = get_xml("https://feeds.arstechnica.com/arstechnica/index")
    entries = xml['rss']['channel']['item']
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="Ars Technica",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=entry["category"],
                authors=[entry["dc:creator"]],
                data=strip_html(entry['content:encoded'])
                    .removesuffix("Comments")
                    .strip()
                    .removesuffix("Read full article")
                    .strip(),
                url=entry["link"],
                _pub_date=normalize_date(entry["pubDate"]),
            )
        )
    return written_content


def read_hackaday() -> List[WrittenContent]:
    xml = get_xml("https://hackaday.com/blog/feed/")
    entries = xml['rss']['channel']['item']
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="Hackaday",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=entry["category"],
                authors=[entry["dc:creator"]],
                data=strip_html(entry['content:encoded']),
                url=entry["link"],
                _pub_date=normalize_date(entry["pubDate"]),
            )
        )
    return written_content


def read_daring_fireball() -> List[WrittenContent]:
    xml = get_xml("https://daringfireball.net/feeds/main")
    entries = xml["feed"]["entry"]
    written_content = []
    for entry in entries:
        # We want Gruber's pieces, not others'
        if "sponsors" in entry["id"] or "linked" in entry["id"]:
            continue

        url= None
        for link in entry["link"]:
            if link["@rel"] == "shorturl":
                url = link["@href"]
        assert url

        written_content.append(
            WrittenContent(
                source="Daring Fireball",
                title=strip_html(entry["title"]),
                tags=[],
                type=randomize_written_content_type_str(),
                authors=get_authors(entry),
                data=strip_html(entry["content"]["#text"]),
                url=url,
                _pub_date=normalize_date(entry["published"]),
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
Authors: {",".join(content.authors)}"""

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
        footer_1=f"Written by {", ".join(content.authors)}",
        footer_2=content.pub_date.strftime("%a, %d %b %Y, %I:%M:%S %p"),
        narrator=voice,
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
