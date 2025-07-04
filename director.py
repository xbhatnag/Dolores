import argparse
import dataclasses
import json
import logging
from datetime import datetime, timedelta, timezone
from queue import Queue
from zoneinfo import ZoneInfo

from dateutil.parser import parse as parse_date
from flask import Flask

from written_content import spawn_written_content_researcher

queue: Queue = Queue()
app = Flask(__name__)


@app.route("/next")
def get_next_script():
    logging.info("Waiting for next script...")
    next_script = queue.get()
    json_dict = dataclasses.asdict(next_script)
    return json.dumps(json_dict)


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

    after = now() - timedelta(days=3)
    if args.after:
        after = parse_date(args.after)

    spawn_written_content_researcher(queue, after)

    # Serve HTTP server
    app.run(host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
