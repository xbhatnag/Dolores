from typing import List

import requests
import xmltodict
import html

from structs import PageMetadata

from pymongo.database import Collection
from pymongo.errors import BulkWriteError
from datetime import datetime, timezone

from threading import Thread
import logging
import random
import time
import dataclasses
from bs4 import BeautifulSoup


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


class RssProvider:
    collection: Collection
    after: datetime
    thread: Thread
    logger: logging.Logger

    def __init__(self, collection: Collection, after: datetime):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collection = collection
        self.after = after
        self.thread = Thread(
            name=self.__class__.__name__.lower(),
            target=self.rss_loop,
        )
        self.thread.daemon = True
        self.thread.start()

    def get_rss(self) -> List[PageMetadata]:
        return []

    def rss_loop(self):
        self.logger.info("Starting RSS Loop")
        while True:
            try:
                all_metadata: List[PageMetadata] = self.get_rss()

                # Filter and convert to JSON dicts
                new_metadata = [
                    dataclasses.asdict(a)
                    for a in filter(
                        lambda a: a.published_after(self.after), all_metadata
                    )
                ]

                self.after = datetime.now().astimezone(timezone.utc)

                self.logger.info("Read %d RSS articles", len(new_metadata))

                # Commit to MongoDB
                if new_metadata:
                    self.collection.insert_many(new_metadata, ordered=False)
            except BulkWriteError as bwe:
                for error in bwe.details["writeErrors"]:
                    if error["code"] == 11000:
                        self.logger.warning("Duplicate article")
                    else:
                        self.logger.error("Bulk write error: %s", error)
                        raise bwe
            except Exception as e:
                self.logger.error("Failed to fetch RSS: %s", e)

            # Sleep for 5 to 10 minutes
            duration = random.randint(5 * 60, 10 * 60)
            self.logger.info(
                "Sleeping for %d minutes, %d seconds", duration // 60, duration % 60
            )
            time.sleep(duration)



class RedditTech(RssProvider):
    def get_rss(self) -> List[PageMetadata]:
        xml = get_xml("https://www.reddit.com/r/technology.rss")
        entries = xml["feed"]["entry"]
        metadata = []

        for entry in entries:
            content = entry["content"]["#text"]
            soup = BeautifulSoup(content, features="html.parser")
            links = soup.find_all("a", href=True)

            # The first part is the title
            title = entry["title"]
            title_parts = title.split("|")
            title = title_parts[0]

            for link in links:
                if "[link]" in link.get_text():
                    metadata.append(
                        PageMetadata.from_raw(
                            source="Reddit",
                            title=title,
                            url=link["href"],
                            date=entry["published"],
                            discussion_url=entry["link"]["@href"],
                        )
                    )
        return metadata


class TheVerge(RssProvider):
    def get_rss(self) -> List[PageMetadata]:
        xml = get_xml("https://www.theverge.com/rss/index.xml")
        entries = xml["feed"]["entry"]
        metadata = []

        for entry in entries:
            metadata.append(
                PageMetadata.from_raw(
                    source="The Verge",
                    title=entry["title"]["#text"],
                    url=entry["link"]["@href"],
                    date=entry["published"],
                    discussion_url=entry["link"]["@href"] + "#comments",
                )
            )

        return metadata

class Hackaday(RssProvider):
    def get_rss(self) -> List[PageMetadata]:
        xml = get_xml("https://hackaday.com/blog/feed/")
        entries = xml["rss"]["channel"]["item"]
        metadata = []
        for entry in entries:
            metadata.append(
                PageMetadata.from_raw(
                    source="Hackaday",
                    title=entry["title"],
                    url=entry["link"],
                    date=entry["pubDate"],
                    discussion_url=entry["link"] + "#comments",
                )
            )
        return metadata


class XdaDevelopers(RssProvider):
    def get_rss(self) -> List[PageMetadata]:
        xml = get_xml("https://www.xda-developers.com/feed/")
        entries = xml["rss"]["channel"]["item"]
        metadata = []
        for entry in entries:
            metadata.append(
                PageMetadata.from_raw(
                    source="XDA Developers",
                    title=entry["title"],
                    url=entry["link"],
                    date=entry["pubDate"],
                    discussion_url=entry["link"] + "#threads",
                )
            )
        return metadata

# class ArsTechnica(RssProvider):
#     def get_rss(self) -> List[PageMetadata]:
#         xml = get_xml("https://feeds.arstechnica.com/arstechnica/index")
#         entries = xml["rss"]["channel"]["item"]
#         metadata = []
#         for entry in entries:
#             metadata.append(
#                 PageMetadata.from_raw(
#                     source="Ars Technica",
#                     title=entry["title"],
#                     url=entry["link"],
#                     date=entry["pubDate"],
#                     discussion_url="",
#                 )
#             )
#         return metadata




# class Engadget(RssProvider):
#     def get_rss(self) -> List[PageMetadata]:
#         xml = get_xml("https://www.engadget.com/rss-full.xml")
#         entries = xml["rss"]["channel"]["item"]
#         metadata = []
#         for entry in entries:
#             metadata.append(
#                 PageMetadata.from_raw(
#                     source="Engadget",
#                     title=entry["title"],
#                     url=entry["link"],
#                     date=entry["pubDate"],
#                     discussion_url="",
#                 )
#             )
#         return metadata


# class MitTechReview(RssProvider):
#     def get_rss(self) -> List[PageMetadata]:
#         xml = get_xml("https://www.technologyreview.com/feed/")
#         entries = xml["rss"]["channel"]["item"]
#         metadata = []
#         for entry in entries:
#             metadata.append(
#                 PageMetadata.from_raw(
#                     source="MIT Technology Review",
#                     title=entry["title"],
#                     url=entry["link"],
#                     date=entry["pubDate"],
#                     discussion_url="",
#                 )
#             )
#         return metadata


# class OsNews(RssProvider):
#     def get_rss(self) -> List[PageMetadata]:
#         xml = get_xml("http://www.osnews.com/files/recent.xml")
#         entries = xml["rss"]["channel"]["item"]
#         metadata = []
#         for entry in entries:
#             metadata.append(
#                 PageMetadata.from_raw(
#                     source="OS News",
#                     title=entry["title"],
#                     url=entry["link"],
#                     date=entry["pubDate"],
#                     discussion_url="",
#                 )
#             )
#         return metadata


# class TechRadar(RssProvider):
#     def get_rss(self) -> List[PageMetadata]:
#         xml = get_xml("https://www.techradar.com/rss")
#         entries = xml["rss"]["channel"]["item"]
#         metadata = []
#         for entry in entries:
#             if "Wordle" in entry["title"]:
#                 continue
#             if "NYT" in entry["title"]:
#                 continue

#             metadata.append(
#                 PageMetadata.from_raw(
#                     source="TechRadar",
#                     title=entry["title"],
#                     url=entry["link"],
#                     date=entry["pubDate"],
#                     discussion_url="",
#                 )
#             )
#         return metadata


# class BBC(RssProvider):
#     def get_rss(self) -> List[PageMetadata]:
#         xml = get_xml("http://feeds.bbci.co.uk/news/rss.xml")
#         entries = xml["rss"]["channel"]["item"]
#         metadata = []
#         for entry in entries:
#             metadata.append(
#                 PageMetadata.from_raw(
#                     source="BBC",
#                     title=entry["title"],
#                     url=entry["link"],
#                     date=entry["pubDate"],
#                     discussion_url="",
#                 )
#             )
#         return metadata


# def read_daring_fireball() -> List[PageMetadata]:
#     xml = get_xml("https://daringfireball.net/feeds/main")
#     entries = xml["feed"]["entry"]
#     metadata = []
#     for entry in entries:
#         # We want Gruber's pieces, not others'
#         if "sponsors" in entry["id"] or "linked" in entry["id"]:
#             continue

#         url = None
#         for link in entry["link"]:
#             if link["@rel"] == "shorturl":
#                 url = link["@href"]
#         assert url

#         metadata.append(
#             PageMetadata(
#                 source="Daring Fireball",
#                 title=entry["title"],
#                 tags=[],
#                 authors=get_authors(entry),
#                 text=entry["content"]["#text"],
#                 url=url,
#                 _pub_date=entry["published"],
#             )
#         )

#     return metadata