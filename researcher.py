import time
from typing import List
import feedparser
import bs4
from dateutil.parser import parse as parse_date
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from jockey_types import Article
from jockey_sockets import *
import logging

def strip_html(html: str) -> str:
    # Remove HTML tags and decode HTML entities
    soup = bs4.BeautifulSoup(html, features="html.parser")
    text = soup.get_text()
    return text.strip()

def read_the_verge_long_form() -> List[Article]:
    feed = feedparser.parse('https://www.theverge.com/rss/index.xml')
    articles = []
    for entry in feed.entries:
        summary = entry.summary
        articles.append(Article(
            source='The Verge',
            title=strip_html(entry.title),
            author=entry.author,
            content=strip_html(summary),
            url=entry.link,
            pub_date=parse_date(entry.published)
        ))
    return articles

def num_words(input: str):
    return len(input.split())

def read_the_verge_quick_posts() -> List[Article]:
    feed = feedparser.parse('https://www.theverge.com/rss/quickposts')
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.summary)
        if (num_words(content)) <= 30:
            # Quick post doesn't have enough content for AI to work with.
            # SKIP!
            logging.info(f"Skipping small article from The Verge")
            continue
        # TODO: Disable informal opinions for short content, not enough
        # data to work with.

        articles.append(Article(
            source='The Verge',
            title=strip_html(entry.title),
            author=entry.author,
            content=content,
            url=entry.link,
            pub_date=parse_date(entry.published)
        ))
    return articles

def read_ars_technica() -> List[Article]:
    feed = feedparser.parse('https://feeds.arstechnica.com/arstechnica/index')
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content[0].value)
        content = content.removesuffix('Comments').strip()
        content = content.removesuffix('Read full article').strip()
        articles.append(Article(
            source='Ars Technica',
            title=entry.title,
            author=entry.author,
            content=content,
            url=entry.link.strip(),
            pub_date=parse_date(entry.published)
        ))
    return articles

def read_hackaday() -> List[Article]:
    feed = feedparser.parse('https://hackaday.com/blog/feed/')
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content[0].value)
        articles.append(Article(
            source='Hack A Day',
            title=entry.title,
            author=entry.author,
            content=content,
            url=entry.link.strip(),
            pub_date=parse_date(entry.published)
        ))
    return articles

def read_daring_fireball() -> List[Article]:
    feed = feedparser.parse('https://daringfireball.net/feeds/main')
    articles = []
    for entry in feed.entries:
        content = strip_html(entry.content[0].value)
        
        # We want Gruber's pieces, not others'
        if "sponsors" in entry.id or "linked" in entry.id:
            continue

        title = getattr(entry, 'title', '')

        # What in god's name is this?
        if not title:
            continue

        # He does this sometimes
        title = title.removeprefix("★ ")

        articles.append(Article(
            source='Daring Fireball',
            title=title,
            author=entry.author,
            content=content,
            url=entry.link.strip(),
            pub_date=parse_date(entry.published)
        ))
    return articles

def today_utc() -> datetime:
    # We know we are in west coast.
    # Normalize it to UTC.
    return datetime.now(tz=ZoneInfo("America/Los_Angeles")).astimezone(timezone.utc)

def main():
    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Welcome to Jockey! I'm the researcher.")
    logging.info("Waiting for script writer to connect...")

    server_socket = create_server_socket("jockey_researcher")
    script_writer, addr = server_socket.accept()
    logging.info("New connection: %s", addr)
    
    # When starting for the first time,
    # Don't include articles more than 3 days old
    last_checked = today_utc() - timedelta(days = 3)

    def is_new_article(a: Article) -> bool:
        # A new article would be one that is newer than the last time
        # we tried to pull articles.
        return (last_checked is None) or (a.pub_date > last_checked)

    while True:
        logging.info("Starting new research cycle!")
        logging.info("Ignoring pieces older than %s", last_checked)

        logging.info("Collecting news from sources...")
        the_verge_long_form = read_the_verge_long_form()
        the_verge_quick_posts = read_the_verge_quick_posts()
        ars_technica = read_ars_technica()
        hack_a_day = read_hackaday()
        daring_fireball = read_daring_fireball()

        # Put em all together
        articles = (hack_a_day + 
            the_verge_quick_posts +
            the_verge_long_form +
            ars_technica +
            daring_fireball)
        
        # Normalize all publishing dates to UTC
        for article in articles:
            article.pub_date = article.pub_date.astimezone(timezone.utc)
        
        # Sort by publishing date
        articles.sort(key=lambda a: a.pub_date, reverse=True)        

        # Add them to the queue for script writing
        new_articles = list(filter(lambda a: is_new_article(a), articles))

        # TODO: Ask Gemini to build context around the article
        logging.info("%d new articles researched!", len(new_articles))

        # Push these articles out via the socket
        for article in articles:
            send_object(article, script_writer)

        # Set the last time we did research.
        logging.info("Research complete! Taking a break...")
        last_checked = today_utc()
        time.sleep(60 * 10)

if __name__ == "__main__":
    main()