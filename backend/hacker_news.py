import requests
import argparse
import logging
import urllib.parse
import bs4
from pymongo import MongoClient
from pymongo.database import Collection
from structs import PageMetadata
from datetime import datetime
import random
import time
import dataclasses
from enum import Enum


def get_top_story_ids():
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    ids = response.json()
    assert isinstance(ids, list)
    ids = [int(id) for id in ids][:50]
    logging.info("Got %d stories", len(ids))
    return ids


class HNType(Enum):
    Blog = 0
    Project = 1
    Unknown = 2


def classify(title: str, url_str: str) -> HNType:
    url = urllib.parse.urlparse(url_str)

    assert url.hostname

    if title.startswith("Show HN"):
        return HNType.Project

    if not url.path:
        # Most likely some kind of project.
        # Only those are at the root.
        return HNType.Project

    if url.hostname.endswith("github.com"):
        return HNType.Project

    if url.hostname.endswith("wordpress.com"):
        return HNType.Blog

    if url.hostname.endswith("substack.com"):
        return HNType.Blog

    if url.hostname.endswith("medium.com"):
        return HNType.Blog

    if url.hostname.endswith("lwn.net"):
        return HNType.Blog

    if url.hostname.startswith("blog."):
        return HNType.Blog

    if url.path.endswith(".pdf"):
        # Don't bother with PDFs yet
        return HNType.Unknown

    if "/blog/" in url.path:
        return HNType.Blog

    if "/post/" in url.path:
        return HNType.Blog

    # If there is an "Author" tag on this page
    # it's most likely a blog
    try:
        html_page = get_html_page(url_str)
    except:
        return HNType.Unknown

    author = html_page.find("meta", {"name": "author"})

    if isinstance(author, bs4.Tag):
        return HNType.Blog

    return HNType.Unknown


def get_html_page(url: str):
    response = requests.get(url)
    html_page = bs4.BeautifulSoup(response.content, features="html.parser")
    return html_page


def hn_loop(collection: Collection, global_ids: set[int]):
    while True:
        ids = get_top_story_ids()
        new_ids = list(filter(lambda id: id not in global_ids, ids))
        global_ids.update(new_ids)

        for id in new_ids:
            response = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{id}.json"
            )
            metadata = response.json()
            if metadata["type"] != "story":
                continue

            if "url" not in metadata:
                continue

            title = metadata["title"]
            url = metadata["url"]
            date = datetime.fromtimestamp(metadata["time"]).isoformat()

            page_type = classify(title, url)

            if page_type == HNType.Blog:
                metadata = PageMetadata.from_raw(url, "Hacker News", title, date)
                try:
                    collection.insert_one(dataclasses.asdict(metadata))
                    logging.info("✅ Inserted: %s", title)
                except:
                    logging.error("❗️ Could not insert: %s", title)
                    continue
            else:
                logging.info("❌ %s: %s", page_type, title)

        # Sleep for 2 to 5 minutes
        duration = random.randint(60 * 2, 60 * 5)
        logging.info(
            "Sleeping for %d minutes, %d seconds...", duration // 60, duration % 60
        )
        time.sleep(duration)


def main():
    parser = argparse.ArgumentParser(description="Hacker News Observer")
    parser.parse_args()

    logging.basicConfig(format="%(asctime)s | %(levelname)-7s | %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client.dolores
    collection = db.page_metadata

    global_ids: set[int] = set()
    hn_loop(collection, global_ids)


if __name__ == "__main__":
    main()
