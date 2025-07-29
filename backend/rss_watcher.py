import argparse
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from rss_providers import *
from pymongo import MongoClient

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


def now() -> datetime:
    return datetime.now().astimezone(ZoneInfo("America/Los_Angeles"))


def main():
    parser = argparse.ArgumentParser(description="RSS Watcher")
    parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s | %(levelname)-7s | %(name)-15s | %(message)s"
    )
    logging.getLogger().setLevel(logging.INFO)

    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client.dolores
    collection = db.rss

    # Set the time after which to fetch news
    after = now() - timedelta(days=1)

    providers = []
    for provider_class in ALL_PROVIDERS:
        provider = provider_class(collection, after)
        providers.append(provider)

    for provider in providers:
        provider.thread.join()
        logging.info(f"{provider.__class__.__name__} finished processing.")


if __name__ == "__main__":
    main()
