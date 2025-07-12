import dataclasses
import logging
import time
import urllib
import urllib.parse
from datetime import datetime
from queue import Queue
from typing import List

import requests
from google import genai
from google.cloud import texttospeech
from playwright.sync_api import sync_playwright

from script import Script
from tts import choose_random_voice, generate_audio


@dataclasses.dataclass(eq=False)
class InterestingPage:
    hn_id: int
    title: str
    url: str
    screenshot: str

    def __eq__(self, value):
        return isinstance(value, InterestingPage) and self.hn_id == value.hn_id

    def __hash__(self):
        return self.hn_id


def take_screenshot(page, url: urllib.parse.ParseResult, index: int) -> str:
    page.goto(url.geturl())
    data = page.screenshot()
    with open(f"/tmp/page_{index}.png", "wb") as f:
        f.write(data)
        f.close()


def is_interesting(
    title: str, url: urllib.parse.ParseResult, score: int, classifier: genai.chats.Chat
) -> bool:
    if score < 100:
        # we have high standards
        return False

    if "blog" in url.geturl():
        return True

    if url.netloc.endswith("substack.com"):
        return True

    logging.info("Consulting AI classifier...")
    prompt = f"""Title={title}\nDomain={url.netloc}"""

    response = classifier.send_message(
        message=prompt,
    )

    return response.text == "true"


def get_interesting_pages(
    classifier: genai.chats.Chat, seen: list[int]
) -> List[InterestingPage]:
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    top_ids: list[int] = response.json()

    for id in top_ids:
        if id in seen:
            logging.info("Already seen %d", id)
            top_ids.remove(id)
        else:
            seen.append(id)

    logging.info("Looking at %s new HN posts", len(top_ids))

    interesting_pages: List[InterestingPage] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for index, hn_id in enumerate(top_ids):
            response = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json"
            )

            page_data = response.json()
            title = page_data["title"]
            url = urllib.parse.urlparse(page_data["url"])
            score = page_data["score"]

            if is_interesting(title, url, score, classifier):
                logging.info("✅ %s [%s][%d]", title, url.geturl(), score)
                screenshot_path = ""
                try:
                    screenshot_path = take_screenshot(page, url, index)
                except Exception as e:
                    logging.error("Unable to capture screenshot: %s", e)
                interesting_pages.append(
                    InterestingPage(
                        hn_id=hn_id, title=title, url=url, screenshot=screenshot_path
                    )
                )
            else:
                logging.info("❌ %s [%s][%d]", title, url.geturl(), score)

        browser.close()

    return interesting_pages


def create_script(
    tts_client: texttospeech.TextToSpeechClient,
    chat: genai.chats.Chat,
    page: InterestingPage,
    filename: str,
):
    # Pick a voice for the TTS
    voice = choose_random_voice()

    # Ask Gemini to write the script
    prompt = f"""
Title: {page.title}
Summary: {page.summary}
"""

    response = chat.send_message(
        message=prompt,
    )
    audio_file = generate_audio(tts_client, response.text, filename, voice)

    return Script(display_text=response.text, audio_file=audio_file)


def research_loop(queue: Queue):
    logging.info("Reading prompts...")
    with open("./trendy/classifier_prompt.md") as f:
        classifier_prompt = f.read()

    classifier = genai.Client(
        vertexai=True,
        project="dolores-cb057",
        location="us-west1",
        http_options=genai.types.HttpOptions(api_version="v1"),
    ).chats.create(
        model="gemini-2.5-pro",
        config=genai.types.GenerateContentConfig(
            system_instruction=classifier_prompt,
            response_mime_type="application/json",
            response_schema=bool,
        ),
    )

    count = 0

    seen = []
    while True:
        pages = get_interesting_pages(classifier, seen)
        time.sleep(60)

    # for page in trending_pages:
    #     logging.info("%s: %s", page.title, page.summary)

    # for page in trending_pages:
    #     script = create_script(tts, chat, page, f"{count}_trend")
    #     queue.put(script)

    #     count += 1

    #     # Wait until we're running out of content
    #     logging.info("Trendy is taking a 30 minute break...")
    #     time.sleep(60 * 30)
