import logging
import random
import threading
import time
from queue import Queue

import requests
import datetime

from script import Script


def get_last_xkcd():
    response = requests.get("https://xkcd.com/info.0.json")
    response.raise_for_status()
    return response.json()


def get_xkcd(id: int):
    response = requests.get(f"https://xkcd.com/{id}/info.0.json")
    response.raise_for_status()
    return response.json()


def create_script():
    last_id = get_last_xkcd()["num"]
    id = random.randint(0, last_id)
    xkcd = get_xkcd(id)
    image = requests.get(xkcd["img"]).content
    title = xkcd["safe_title"]

    text = random.choice(
        [
            f"And now ... here's XKCD comic number {id}!",
            f'Here\'s XKCD comic {id}, titled "{title}"!',
            f"Time for some XKCD. Here's comic {id}!",
            f'XKCD has a new comic titled "{title}". Take a look!',
            f'XKCD has got a new comic ... Number {id} titled "{title}"!',
        ]
    )

    pub_date = datetime.datetime(
        int(xkcd["year"]), int(xkcd["month"]), int(xkcd["day"])
    )

    return Script(
        title=f"[XKCD #{id}] {title}",
        description=xkcd["alt"],
        hero=image,
        qr_code=f"https://xkcd.com/{id}",
        footer_1=pub_date.strftime("%a, %d %b %Y"),
        footer_2="",
        audio=text,
    )


def xkcd_loop(queue: Queue):
    count = 0

    while True:
        logging.info("Getting new XKCD comic!")

        script = create_script()
        queue.put(script)

        count += 1

        # Wait until we're running out of content
        logging.info("XKCD is taking a 30 minute break...")
        time.sleep(60 * 30)


def spawn_xkcd(queue: Queue) -> threading.Thread:
    logging.info("Spawning XKCD")
    thread = threading.Thread(target=xkcd_loop, args=(queue,))
    thread.daemon = True
    thread.start()
    return thread
