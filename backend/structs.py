import dataclasses
import logging
from datetime import datetime, timezone
from typing import List

import bs4
from dateutil.parser import parse as parse_date
from playwright.sync_api import Page, sync_playwright
from pydantic import BaseModel


def get_favicon_url(page) -> str:
    return page.evaluate(
        """() => {
        const link = document.querySelector('link[rel="icon"], link[rel="shortcut icon"]');
        if (link) {
            const href = link.href;
            if (href.startsWith('http')) {
                return href;
            } else if (href.startsWith('/')) {
                const urlObj = new URL(document.location.href);
                return urlObj.protocol + '//' + urlObj.host + href;
            } else {
                return document.location.href + '/' + href;
            }
        }
        return null;
    }"""
    )


def get_text_by_classname(page: Page, classname: str) -> str:
    elements = page.locator(f"{classname}")

    all_text = []
    for i in range(elements.count()):
        all_text.append(elements.nth(i).inner_text())
    all_text = "\n\n".join(all_text)
    return all_text.strip()


def strip_html(html: str) -> str:
    # Remove HTML tags and decode HTML entities
    soup = bs4.BeautifulSoup(html, features="html.parser")
    text = soup.get_text()
    return text.strip()


@dataclasses.dataclass
class RssContent:
    _id: str
    source: str
    title: str
    authors: List[str]
    tags: List[str]
    text: str
    url: str
    pub_date: str

    @staticmethod
    def from_raw(
        url: str,
        source: str,
        title: str,
        authors: List[str],
        tags: List[str],
        text: str,
        pub_date: str,
    ):
        _id = url

        # Fix the title
        title = strip_html(title)

        # Fix the date
        pub_date = parse_date(pub_date).astimezone(timezone.utc).isoformat()

        # Fix the text
        text = strip_html(text)

        source = source
        authors = authors
        tags = tags
        url = url

        return RssContent(
            _id=_id,
            source=source,
            title=title,
            authors=authors,
            tags=tags,
            text=text,
            url=url,
            pub_date=pub_date,
        )

    def published_after(self, cmp_date: datetime) -> bool:
        return datetime.fromisoformat(self.pub_date) > cmp_date


@dataclasses.dataclass
class PageContent:
    _id: str
    source: str
    title: str
    url: str
    text: str
    favicon_url: str
    pub_date: str

    @staticmethod
    def from_rss(rss: RssContent):
        logging.info("Parsing %s", rss.url)
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch()
                page = browser.new_page()
                page.goto(rss.url)
                favicon_url = get_favicon_url(page)
                page_text: str = get_text_by_classname(page, "p")
                page_content = PageContent(
                    rss._id, rss.source, rss.title, rss.url, page_text, favicon_url, rss.pub_date
                )
                logging.info("Parse complete: %s", rss.url)
                return page_content
        except Exception as e:
            logging.error("Failed to parse %s: %s", rss.url, e)
            return None


class LlmAnalysis(BaseModel):
    takeaways: list[str]
    search_terms: set[str]
    happy_scale: int
    impact_scale: int
    breaking_news: bool


@dataclasses.dataclass
class Analysis:
    _id: str
    title: str
    url: str
    favicon_url: str
    takeaways: list[str]
    search_terms: list[str]
    happy_scale: int
    impact_scale: int
    breaking_news: bool
    source: str
    pub_date: str

    @staticmethod
    def from_llm_analysis(llm_analysis: LlmAnalysis, page_content: PageContent):
        return Analysis(
            _id=page_content._id,
            title=page_content.title,
            url=page_content.url,
            favicon_url=page_content.favicon_url,
            takeaways=llm_analysis.takeaways,
            search_terms=list(llm_analysis.search_terms),
            happy_scale=llm_analysis.happy_scale,
            impact_scale=llm_analysis.impact_scale,
            breaking_news=llm_analysis.breaking_news,
            source=page_content.source,
            pub_date=page_content.pub_date,
        )
