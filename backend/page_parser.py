import argparse
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from concurrent.futures import ThreadPoolExecutor, Future
from pymongo import MongoClient
from pymongo.database import Collection

from structs import PageMetadata, PageContent

import dataclasses
import random
import time


class PageParser:
    metadata_collection: Collection
    content_collection: Collection

    def __init__(
        self,
        metadata_collection: Collection,
        content_collection: Collection,
    ):
        self.metadata_collection = metadata_collection
        self.content_collection = content_collection

    def parse(self, metadata: PageMetadata):
        page_content = PageContent.from_metadata(metadata)
        if not page_content:
            logging.error("Failed to parse %s", metadata.url)
            return

        # Add the page content to MongoDB
        self.content_collection.insert_one(dataclasses.asdict(page_content))

    def parse_loop(self):
        logging.info("Starting Parse Loop")
        thread_pool = ThreadPoolExecutor(max_workers=5)

        while True:
            # Send all metadata to the thread pool for parsing
            futures: list[Future] = []
            for metadata_str in self.metadata_collection.find():
                metadata = PageMetadata(**metadata_str)

                if self.content_collection.find_one({"_id": metadata._id}):
                    continue

                future = thread_pool.submit(self.parse, metadata)
                futures.append(future)

            logging.info("Waiting for all pages to parse...")
            for future in futures:
                future.result()

            # Sleep for 2 to 5 minutes
            duration = random.randint(60 * 2, 60 * 5)
            logging.info(
                "Sleeping for %d minutes, %d seconds...", duration // 60, duration % 60
            )
            time.sleep(duration)


def now() -> datetime:
    return datetime.now().astimezone(ZoneInfo("America/Los_Angeles"))


def main():
    parser = argparse.ArgumentParser(description="Page Parser")
    parser.parse_args()

    logging.basicConfig(format="%(asctime)s | %(levelname)-7s | %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client.dolores
    metadata_collection = db.page_metadata
    content_collection = db.page_content

    page_parser = PageParser(metadata_collection, content_collection)
    page_parser.parse_loop()


if __name__ == "__main__":
    main()
