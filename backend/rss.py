import dataclasses
import io
import logging
import random
import time
from datetime import datetime, timezone
from queue import Queue
from typing import List

import json
import requests
import xmltodict
from dateutil.parser import parse as parse_date
from playwright.sync_api import Page, ViewportSize, sync_playwright

from structs import NewsStory, Analysis, WrittenContent

from dataclasses import asdict

from threading import Thread


def take_screenshot(page: Page, url: str) -> bytes:
    while True:
        try:
            page.goto(url)
            return page.screenshot()
        except:
            # Give it another go in a few seconds
            time.sleep(10)
            pass


def randomize_written_content_type_str() -> str:
    return random.choice(["article", "piece", "story"])


def get_authors(entry: dict) -> List[str]:
    if "dc:creator" in entry:
        return [entry["dc:creator"]]
    elif "author" in entry:
        if isinstance(entry["author"], list):
            return [author["name"] for author in entry["author"]]
        elif isinstance(entry["author"], dict) and "name" in entry["author"]:
            return [entry["author"]["name"]]
        elif isinstance(entry["author"], str):
            return [entry["author"]]
    raise AssertionError("Unknown author type")


def get_xml(url: str) -> dict:
    response = requests.get(url, headers={"User-Agent": "Dolores/1.0"})
    response.raise_for_status()
    rss = xmltodict.parse(response.text)
    return rss


def get_categories(entry: dict) -> List[str]:
    if "catgory" not in entry:
        return []
    if isinstance(entry["category"], str):
        return [entry["category"]]
    if isinstance(entry["category"], dict):
        return [entry["category"]["@term"]]
    if isinstance(entry["category"], list):
        if entry["category"]:
            return []
        elif isinstance(entry["category"][0], str):
            return entry["category"]
        else:
            return [category["@term"] for category in entry["category"]]
    assert "Unexpected"
    return []


def read_the_verge_long_form() -> List[WrittenContent]:
    xml = get_xml("https://www.theverge.com/rss/index.xml")
    entries = xml["feed"]["entry"]
    written_content = []

    for entry in entries:
        written_content.append(
            WrittenContent(
                source="The Verge",
                title=entry["title"]["#text"],
                tags=get_categories(entry),
                type=randomize_written_content_type_str(),
                authors=get_authors(entry),
                text=entry["content"]["#text"],
                url=entry["link"]["@href"],
                _pub_date=entry["published"],
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
                title=entry["title"]["#text"],
                tags=get_categories(entry),
                type=randomize_written_content_type_str(),
                authors=get_authors(entry),
                text=entry["content"]["#text"],
                url=entry["link"]["@href"],
                _pub_date=entry["published"],
            )
        )
    return written_content


def read_ars_technica() -> List[WrittenContent]:
    xml = get_xml("https://feeds.arstechnica.com/arstechnica/index")
    entries = xml["rss"]["channel"]["item"]
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="Ars Technica",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=get_categories(entry),
                authors=get_authors(entry),
                text=entry["content:encoded"],
                url=entry["link"],
                _pub_date=entry["pubDate"],
            )
        )
    return written_content


def read_hackaday() -> List[WrittenContent]:
    xml = get_xml("https://hackaday.com/blog/feed/")
    entries = xml["rss"]["channel"]["item"]
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="Hackaday",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=get_categories(entry),
                authors=get_authors(entry),
                text=entry["content:encoded"],
                url=entry["link"],
                _pub_date=entry["pubDate"],
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

        url = None
        for link in entry["link"]:
            if link["@rel"] == "shorturl":
                url = link["@href"]
        assert url

        written_content.append(
            WrittenContent(
                source="Daring Fireball",
                title=entry["title"],
                tags=[],
                type=randomize_written_content_type_str(),
                authors=get_authors(entry),
                text=entry["content"]["#text"],
                url=url,
                _pub_date=entry["published"],
            )
        )

    return written_content


def read_engadget() -> List[WrittenContent]:
    xml = get_xml("https://www.engadget.com/rss-full.xml")
    entries = xml["rss"]["channel"]["item"]
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="Engadget",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=get_categories(entry),
                authors=get_authors(entry),
                text=entry["description"]["#text"],
                url=entry["link"],
                _pub_date=entry["pubDate"],
            )
        )
    return written_content


def read_mit_tech_review() -> List[WrittenContent]:
    xml = get_xml("https://www.technologyreview.com/feed/")
    entries = xml["rss"]["channel"]["item"]
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="MIT Technology Review",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=get_categories(entry),
                authors=get_authors(entry),
                text=entry["content:encoded"],
                url=entry["link"],
                _pub_date=entry["pubDate"],
            )
        )
    return written_content


def read_os_news() -> List[WrittenContent]:
    xml = get_xml("http://www.osnews.com/files/recent.xml")
    entries = xml["rss"]["channel"]["item"]
    written_content = []
    for entry in entries:
        written_content.append(
            WrittenContent(
                source="OS News",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=get_categories(entry),
                authors=get_authors(entry),
                text=entry["description"],
                url=entry["link"],
                _pub_date=entry["pubDate"],
            )
        )
    return written_content


def read_techradar() -> List[WrittenContent]:
    xml = get_xml("https://www.techradar.com/rss")
    entries = xml["rss"]["channel"]["item"]
    written_content = []
    for entry in entries:
        if "Wordle" in entry["title"]:
            continue
        if "NYT" in entry["title"]:
            continue

        written_content.append(
            WrittenContent(
                source="TechRadar",
                title=entry["title"],
                type=randomize_written_content_type_str(),
                tags=get_categories(entry),
                authors=get_authors(entry),
                text=entry["content:encoded"],
                url=entry["link"],
                _pub_date=entry["pubDate"],
            )
        )
    return written_content


def read_content_from_rss(after: datetime) -> List[WrittenContent]:
    the_verge_long_form = read_the_verge_long_form()
    # the_verge_quick_posts = read_the_verge_quick_posts()
    ars_technica = read_ars_technica()
    hack_a_day = read_hackaday()
    daring_fireball = read_daring_fireball()
    engadget = read_engadget()
    mit_tech_review = read_mit_tech_review()
    os_news = read_os_news()
    techradar = read_techradar()

    # Put em all together
    all_written_content = (
        hack_a_day
        # + the_verge_quick_posts
        + the_verge_long_form
        + ars_technica
        + daring_fireball
        + engadget
        + mit_tech_review
        + os_news
        + techradar
    )

    # Normalize the content
    for content in all_written_content:
        content.normalize()

    all_written_content = list(
        filter(lambda a: a.published_after(after), all_written_content)
    )
    all_written_content.sort(key=lambda a: a.pub_date, reverse=True)

    return all_written_content


def rss_loop(content_queue: Queue[WrittenContent], after: datetime):
    logging.info("Reading prompts...")

    # Log all articles to a temp file
    with open("/tmp/articles.json", "w") as f:
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
                    json_dict = json.dumps(asdict(content))
                    f.write(json_dict)
                    f.write("\n")
                    f.flush()
                    content_queue.put(content)

            # Take breaks between RSS cycles
            sleep_time = 60 * 5
            logging.info("RSS sleeping for %d seconds", sleep_time)
            time.sleep(sleep_time)


def spawn_rss_thread(content_queue: Queue[WrittenContent], after: datetime) -> Thread:
    logging.info("Spawning RSS Thread")
    thread = Thread(target=rss_loop, args=(content_queue, after))
    thread.daemon = True
    thread.start()
    return thread
