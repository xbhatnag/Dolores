import dataclasses
import logging
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from playwright.sync_api import Page, sync_playwright
from pydantic import BaseModel
import html


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


def get_text_by_classname(page: Page) -> str:
    base = page.locator("p")

    if page.get_by_role("article"):
        article = page.get_by_role("article")
        if article.get_by_role("paragraph"):
            base = page.get_by_role("paragraph")

    all_text = []
    for match in base.all():
        text = match.text_content()
        all_text.append(text)

    return "\n\n".join(all_text)


@dataclasses.dataclass
class PageMetadata:
    _id: str
    source: str
    title: str
    url: str
    date: str

    @staticmethod
    def from_raw(
        url: str,
        source: str,
        title: str,
        date: str,
    ):
        date = parse_date(date).astimezone(timezone.utc).isoformat()
        source = source
        url = url

        return PageMetadata(
            _id=url,
            source=source,
            title=title,
            url=url,
            date=date,
        )

    def published_after(self, cmp_date: datetime) -> bool:
        return datetime.fromisoformat(self.date) > cmp_date


@dataclasses.dataclass
class PageContent:
    _id: str
    source: str
    title: str
    url: str
    text: str
    favicon_url: str
    date: str

    @staticmethod
    def from_metadata(metadata: PageMetadata):
        logging.info("Parsing %s", metadata.url)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            try:
                page.goto(metadata.url)
            except Exception as e:
                logging.error("Failed to parse %s: %s", metadata.url, e)
                return None

            favicon_url = get_favicon_url(page)
            page_text: str = get_text_by_classname(page)
            page_content = PageContent(
                metadata._id,
                metadata.source,
                metadata.title,
                metadata.url,
                page_text,
                favicon_url,
                metadata.date,
            )
            logging.info("Parse complete: %s", metadata.url)
            return page_content


class LlmAnalysis(BaseModel):
    takeaways: list[str]
    search_terms: set[str]


@dataclasses.dataclass
class Analysis:
    _id: str
    takeaways: list[str]
    search_terms: list[str]

    @staticmethod
    def from_llm_analysis(llm_analysis: LlmAnalysis, page_content: PageContent):
        return Analysis(
            _id=page_content._id,
            takeaways=llm_analysis.takeaways,
            search_terms=list(llm_analysis.search_terms),
        )
