import argparse
import base64
import io
import json
import logging
from datetime import datetime, timedelta
from queue import Queue
from zoneinfo import ZoneInfo

from dateutil.parser import parse as parse_date
from flask import Flask
from google.cloud import texttospeech

from rss import spawn_rss_thread
from structs import NewsStory, NewsStories, ApiStory, WrittenContent, Analyzer
from dataclasses import asdict

import base64

tts = texttospeech.TextToSpeechClient()
analyzer = Analyzer()
stories = NewsStories(analyzer)
app = Flask(__name__)
    

@app.route("/next")
def get_next_story():
    logging.info("API Call to /next")
    story: NewsStory = stories.next()
    response = ApiStory(story)
    return asdict(response)

@app.route("/all")
def get_all_stories():
    logging.info("API call to /all")
    story_list = [asdict(ApiStory(story)) for story in stories.all()]
    return story_list

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

    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Dolores Backend!")

    if args.cache:
        with open("/tmp/articles.json") as f:
            lines = f.readlines()
            logging.info("Reading %d cached stories", len(lines))
            for line in lines:
                json_dict = json.loads(line)
                content = WrittenContent(**json_dict)
                stories.queue().put(content)
    else:
        after = now() - timedelta(days=1)
        if args.after:
            if args.after == "now":
                after = now()
            else:
                after = parse_date(args.after)
        spawn_rss_thread(stories.queue(), after)

    # Serve HTTP server
    app.run(host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
