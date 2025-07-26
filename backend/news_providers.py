import logging
import random
import time
from datetime import datetime, timezone
from queue import Queue
from typing import List

import os
import json
import requests
import xmltodict
from playwright.sync_api import Browser, Page, sync_playwright

from structs import RssContent, PageContent

from dataclasses import asdict

from concurrent.futures import ThreadPoolExecutor
from threading import Thread
import uuid
import hashlib


def get_favicon_url(page) -> str:
    return page.evaluate(
        """() => {
        const link = document.querySelector('link[rel="icon"], link[rel="shortcut icon"]');
        if (link) {
            const href = link.href;
            if (href.startsWith('http')) {
                return href;
            } else if (href.startsWith('/')) {
                const urlObj = new URL(document.location.href);
                return urlObj.protocol + '//' + urlObj.host + href;
            } else {
                return document.location.href + '/' + href;
            }
        }
        return null;
    }"""
    )


def get_text_by_classname(page: Page, classname: str) -> str:
    elements = page.locator(f".{classname}")

    all_text = []
    for i in range(elements.count()):
        all_text.append(elements.nth(i).inner_text())
    all_text = "\n\n".join(all_text)
    return all_text


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


class NewsProvider:
    out_queue: Queue
    after: datetime
    thread: Thread
    logger: logging.Logger

    def __init__(
        self, thread_pool: ThreadPoolExecutor, out_queue: Queue, after: datetime
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.out_queue = out_queue
        self.after = after
        self.thread_pool = thread_pool
        self.thread = Thread(
            target=self.rss_loop,
        )
        self.thread.daemon = True
        self.thread.start()

    def get_rss(self) -> List[RssContent]:
        return []

    def get_text_from_page(self, page: Page) -> str:
        return ""

    def rss_loop(self):
        self.logger.info("Starting RSS Loop")
        while True:
            # Sleep for a few seconds for randomness
            time.sleep(random.randint(0, 10))

            try:
                all_rss_content: List[RssContent] = self.get_rss()
            except Exception as e:
                self.logger.error("Could not get RSS content")

            # Normalize all RSS content
            for content in all_rss_content:
                content.normalize()

            new_rss_content = list(
                filter(lambda a: a.published_after(self.after), all_rss_content)
            )

            self.logger.info("Read %d RSS articles", len(new_rss_content))

            for rss_content in new_rss_content:
                # Start off threads to process the individual content
                self.thread_pool.submit(self.parse_page_and_cache, rss_content)

            # We don't want articles older than now
            self.after = datetime.now(tz=timezone.utc)

            # Sleep for 5 to 10 minutes
            time.sleep(random.randint(5 * 60, 10 * 60))

    def write_to_disk(self, rss_content: RssContent, page_content: PageContent):
        try:
            if not os.path.exists("/tmp/articles"):
                os.mkdir("/tmp/articles")
            assert os.path.isdir("/tmp/articles")
            data = rss_content.source + rss_content.title
            md5 = hashlib.md5(data.encode("ascii", errors="ignore")).hexdigest()
            filename = md5 + ".json"
            with open("/tmp/articles/" + filename, "w") as f:
                f.write(json.dumps(asdict(rss_content)))
                f.write("\n")
                f.write(json.dumps(asdict(page_content)))
                f.close()
                self.logger.info("Cached: %s", filename)
        except Exception as e:
            self.logger.error("Failed to cache: %s", e)

    def parse_page_and_cache(self, rss_content: RssContent):
        page_content = self.parse_page(rss_content)
        self.write_to_disk(rss_content, page_content)
        self.out_queue.put((rss_content, page_content))

    def parse_page(self, rss_content: RssContent):
        self.logger.info("Parsing: %s", rss_content.url)
        while True:
            try:
                with sync_playwright() as p:
                    browser = p.firefox.launch()
                    page = browser.new_page()
                    page.goto(rss_content.url)
                    favicon_url = get_favicon_url(page)
                    page_text: str = self.get_text_from_page(page)
                    page_content = PageContent(page_text, favicon_url)
                    self.logger.info("Parse complete: %s", rss_content.url)
                    return page_content
            except Exception as e:
                self.logger.error("Page parse failure: %s", e)
                time.sleep(random.randint(60, 5 * 60))


class TheVerge(NewsProvider):
    def get_rss(self) -> List[RssContent]:
        xml = get_xml("https://www.theverge.com/rss/index.xml")
        entries = xml["feed"]["entry"]
        rss_content = []

        for entry in entries:
            rss_content.append(
                RssContent(
                    source="The Verge",
                    title=entry["title"]["#text"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["content"]["#text"],
                    url=entry["link"]["@href"],
                    _pub_date=entry["published"],
                )
            )

        return rss_content

    def get_text_from_page(self, page: Page) -> str:
        return get_text_by_classname(page, "duet--article--article-body-component")


# def the_verge_quick_posts() -> List[RssContent]:
#     xml = get_xml("https://www.theverge.com/rss/quickposts")
#     entries = xml["feed"]["entry"]
#     rss_content = []
#     for entry in entries:
#         rss_content.append(
#             RssContent(
#                 source="The Verge",
#                 title=entry["title"]["#text"],
#                 tags=get_categories(entry),
#                 authors=get_authors(entry),
#                 text=entry["content"]["#text"],
#                 url=entry["link"]["@href"],
#                 _pub_date=entry["published"],
#             )
#         )
#     return rss_content


# def the_verge_quick_posts_parse_page(page: Page) -> PageContent:
#     # The RSS and page content is the same
#     return PageContent(text="", favicon_url="https://www.theverge.com/favicon.ico")


class ArsTechnica(NewsProvider):

    def get_rss(self) -> List[RssContent]:
        xml = get_xml("https://feeds.arstechnica.com/arstechnica/index")
        entries = xml["rss"]["channel"]["item"]
        rss_content = []
        for entry in entries:
            rss_content.append(
                RssContent(
                    source="Ars Technica",
                    title=entry["title"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["content:encoded"],
                    url=entry["link"],
                    _pub_date=entry["pubDate"],
                )
            )
        return rss_content

    def get_text_from_page(self, page: Page) -> str:
        return get_text_by_classname(page, "post-content")


class Hackaday(NewsProvider):
    def get_rss(self) -> List[RssContent]:
        xml = get_xml("https://hackaday.com/blog/feed/")
        entries = xml["rss"]["channel"]["item"]
        rss_content = []
        for entry in entries:
            rss_content.append(
                RssContent(
                    source="Hackaday",
                    title=entry["title"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["content:encoded"],
                    url=entry["link"],
                    _pub_date=entry["pubDate"],
                )
            )
        return rss_content

    def get_text_from_page(self, page: Page) -> str:
        return get_text_by_classname(page, "entry-content")


# def read_daring_fireball() -> List[RssContent]:
#     xml = get_xml("https://daringfireball.net/feeds/main")
#     entries = xml["feed"]["entry"]
#     rss_content = []
#     for entry in entries:
#         # We want Gruber's pieces, not others'
#         if "sponsors" in entry["id"] or "linked" in entry["id"]:
#             continue

#         url = None
#         for link in entry["link"]:
#             if link["@rel"] == "shorturl":
#                 url = link["@href"]
#         assert url

#         rss_content.append(
#             RssContent(
#                 source="Daring Fireball",
#                 title=entry["title"],
#                 tags=[],
#                 authors=get_authors(entry),
#                 text=entry["content"]["#text"],
#                 url=url,
#                 _pub_date=entry["published"],
#             )
#         )

#     return rss_content


class Engadget(NewsProvider):
    def get_rss(self) -> List[RssContent]:
        xml = get_xml("https://www.engadget.com/rss-full.xml")
        entries = xml["rss"]["channel"]["item"]
        rss_content = []
        for entry in entries:
            rss_content.append(
                RssContent(
                    source="Engadget",
                    title=entry["title"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["description"]["#text"],
                    url=entry["link"],
                    _pub_date=entry["pubDate"],
                )
            )
        return rss_content

    def get_text_from_page(self, page: Page) -> str:
        return get_text_by_classname(page, "caas-body")


class MitTechReview(NewsProvider):
    def get_rss(self) -> List[RssContent]:
        xml = get_xml("https://www.technologyreview.com/feed/")
        entries = xml["rss"]["channel"]["item"]
        rss_content = []
        for entry in entries:
            rss_content.append(
                RssContent(
                    source="MIT Technology Review",
                    title=entry["title"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["content:encoded"],
                    url=entry["link"],
                    _pub_date=entry["pubDate"],
                )
            )
        return rss_content


class OsNews(NewsProvider):
    def get_rss(self) -> List[RssContent]:
        xml = get_xml("http://www.osnews.com/files/recent.xml")
        entries = xml["rss"]["channel"]["item"]
        rss_content = []
        for entry in entries:
            rss_content.append(
                RssContent(
                    source="OS News",
                    title=entry["title"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["description"],
                    url=entry["link"],
                    _pub_date=entry["pubDate"],
                )
            )
        return rss_content


class TechRadar(NewsProvider):
    def get_rss(self) -> List[RssContent]:
        xml = get_xml("https://www.techradar.com/rss")
        entries = xml["rss"]["channel"]["item"]
        rss_content = []
        for entry in entries:
            if "Wordle" in entry["title"]:
                continue
            if "NYT" in entry["title"]:
                continue

            rss_content.append(
                RssContent(
                    source="TechRadar",
                    title=entry["title"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["content:encoded"],
                    url=entry["link"],
                    _pub_date=entry["pubDate"],
                )
            )
        return rss_content


class XdaDevelopers(NewsProvider):
    def get_rss(self) -> List[RssContent]:
        xml = get_xml("https://www.xda-developers.com/feed/")
        entries = xml["rss"]["channel"]["item"]
        rss_content = []
        for entry in entries:
            rss_content.append(
                RssContent(
                    source="XDA Developers",
                    title=entry["title"],
                    tags=get_categories(entry),
                    authors=get_authors(entry),
                    text=entry["content:encoded"],
                    url=entry["link"],
                    _pub_date=entry["pubDate"],
                )
            )
        return rss_content


ALL_PROVIDERS = [
    TheVerge,
    ArsTechnica,
    Engadget,
    TechRadar,
    MitTechReview,
    XdaDevelopers,
    OsNews,
    Hackaday,
]


def spawn_news_providers(
    thread_pool: ThreadPoolExecutor, out_queue: Queue, after: datetime
):
    providers = []
    for provider_class in ALL_PROVIDERS:
        provider = provider_class(thread_pool, out_queue, after)
        providers.append(provider)

    return providers
