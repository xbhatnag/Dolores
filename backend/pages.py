import argparse
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient
from pymongo.database import Collection

from structs import RssContent, PageContent

import dataclasses
import random
import time

class PageParser:
    rss_collection: Collection
    page_collection: Collection

    def __init__(
        self,
        rss_collection: Collection,
        page_collection: Collection,
    ):
        self.rss_collection = rss_collection
        self.page_collection = page_collection

    def parse(self, rss_content: RssContent):
        page_content = PageContent.from_rss(rss_content)
        if not page_content:
            logging.error("Failed to parse %s", rss_content.url)
            return

        # Add the page content to MongoDB
        self.page_collection.insert_one(dataclasses.asdict(page_content))

    def parse_loop(self):
        logging.info("Starting Parse Loop")
        after = None

        while True:
            # Sleep for 2 to 5 minutes
            duration = random.randint(60 * 2, 60 * 5)
            logging.info(
                "Sleeping for %d minutes, %d seconds...", duration // 60, duration % 60
            )
            time.sleep(duration)
            thread_pool = ThreadPoolExecutor(max_workers=5)

            # Send all RSS content to the thread pool for parsing
            for rss_content_str in self.rss_collection.find():
                rss_content = RssContent(**rss_content_str)

                if self.page_collection.find_one({"_id": rss_content._id}):
                    logging.info("Already parsed: %s", rss_content.url)
                    continue

                thread_pool.submit(self.parse, rss_content)

            after = datetime.now(tz=timezone.utc)
            logging.info("Waiting for all pages to parse...")
            thread_pool.shutdown(wait=True)


def now() -> datetime:
    return datetime.now().astimezone(ZoneInfo("America/Los_Angeles"))


def main():
    parser = argparse.ArgumentParser(description="Page Parser")
    parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s | %(levelname)-7s | %(message)s"
    )
    logging.getLogger().setLevel(logging.INFO)

    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client.dolores
    rss_collection = db.rss
    page_collection = db.pages

    page_parser = PageParser(rss_collection, page_collection)
    page_parser.parse_loop()


if __name__ == "__main__":
    main()
