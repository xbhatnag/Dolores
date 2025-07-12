import argparse
import json
import logging
from datetime import datetime, timedelta
from queue import Queue
from zoneinfo import ZoneInfo

from dateutil.parser import parse as parse_date
from flask import Flask

from factoid import spawn_factoid
from journalist import spawn_journalist
from script import Script
from trendy import spawn_trendy
import base64

queue: Queue = Queue()
app = Flask(__name__)


@app.route("/next")
def get_next_script():
    logging.info("Narrator is waiting for next script...")
    script: Script = queue.get()
    b64_audio = base64.b64encode(script.audio).decode("ascii")
    b64_hero = base64.b64encode(script.hero).decode("ascii")
    b64_qr_code = base64.b64encode(script.qr_code).decode("ascii")
    json_data = {
        "title": script.title,
        "description": script.description,
        "audio": b64_audio,
        "hero": b64_hero,
        "qr_code": b64_qr_code,
        "footer_1": script.footer_1,
        "footer_2": script.footer_2,
        "narrator": script.narrator
    }
    return json_data


def now() -> datetime:
    # We know we are in west coast.
    return datetime.now(tz=ZoneInfo("America/Los_Angeles"))


def main():
    global queue

    parser = argparse.ArgumentParser(description="Director")
    parser.add_argument(
        "--after", "-a", type=str, help="Only get articles after this date + time"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=8080, help="Port number for HTTP server"
    )
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Welcome to Jockey! I'm the Director.")

    after = now() - timedelta(days=1)
    if args.after:
        after = parse_date(args.after)

    spawn_journalist(queue, after)
    # spawn_factoid(queue)

    # spawn_trendy(queue)

    # Serve HTTP server
    app.run(host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
