from queue import Queue
from datetime import datetime
import threading
import logging
from .research import research_loop

def spawn_journalist(queue: Queue, after: datetime) -> threading.Thread:
    logging.info("Spawning Journalist")
    thread = threading.Thread(target=research_loop, args=(queue, after))
    thread.daemon = True
    thread.start()
    return thread
