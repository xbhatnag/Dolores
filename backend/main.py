import argparse
import dataclasses
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict

from dateutil.parser import parse as parse_date
from flask import Flask, request

import os
from news_providers import spawn_news_providers
from structs import Newspaper, RssContent, PageContent
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor

newspaper = Newspaper()
app = Flask(__name__)
web_logger = logging.getLogger("API")


@app.route("/next")
def get_next_story():
    web_logger.info("API Call to /next")
    story = newspaper.out_queue.get()
    return story.to_json()


@app.route("/all")
def all_stories():
    web_logger.info("API Call to /all")
    stories = [story.to_json() for story in newspaper.stories]
    return stories


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = (
        "*"  # Or specify your allowed origin
    )
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def now() -> datetime:
    # We know we are in west coast.
    return datetime.now(tz=ZoneInfo("America/Los_Angeles"))


def main():
    parser = argparse.ArgumentParser(description="Dolores")
    parser.add_argument(
        "--after", "-a", type=str, help="Only get articles after this date + time"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=8080, help="Port number for HTTP server"
    )
    parser.add_argument(
        "--cache", "-c", action="store_true", help="Use cached data only"
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s | %(levelname)-5s | %(name)-15s | %(message)s"
    )
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Dolores Backend!")

    # Disable spammy loggers
    to_disable = [
        "SyncLMStudioWebsocket",
        "AsyncWebsocketHandler",
        "werkzeug",
        "AsyncWebsocketThread",
        "httpx",
    ]
    for name in to_disable:
        logging.getLogger(name).disabled = True

    if args.cache:
        files = os.listdir("/tmp/articles")
        logging.info("Reading %d cached articles...", len(files))
        for file in files:
            with open("/tmp/articles/" + file) as f:
                lines = f.readlines()

                json_dict = json.loads(lines[0])
                rss_content = RssContent(**json_dict)

                json_dict = json.loads(lines[1])
                page_content = PageContent(**json_dict)

                newspaper.in_queue.put((rss_content, page_content))
    else:
        after = now() - timedelta(days=1)
        if args.after:
            if args.after == "now":
                after = now()
            else:
                after = parse_date(args.after)
        thread_pool = ThreadPoolExecutor(max_workers=5)
        spawn_news_providers(thread_pool, newspaper.in_queue, after)

    # Serve HTTP server
    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
