from queue import Queue
import threading
import logging
from .research import research_loop

def spawn_trendy(queue: Queue) -> threading.Thread:
    logging.info("Spawning Trendy")
    thread = threading.Thread(target=research_loop, args=(queue,))
    thread.daemon = True
    thread.start()
    return thread