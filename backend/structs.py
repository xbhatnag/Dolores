import dataclasses
from typing import List

import re
import bs4
from threading import Thread

from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from pydantic import BaseModel
from queue import Queue
import lmstudio as lms
from pydantic import BaseModel

import logging
import uuid


def strip_html(html: str) -> str:
    # Remove HTML tags and decode HTML entities
    soup = bs4.BeautifulSoup(html, features="html.parser")
    text = soup.get_text()
    return text.strip()


@dataclasses.dataclass
class RssContent:
    source: str
    title: str
    authors: List[str]
    tags: List[str]
    text: str
    url: str
    _pub_date: str

    def __getattr__(self, name):
        if name == "pub_date":
            return datetime.fromisoformat(self._pub_date)
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

    def published_after(self, cmp_date: datetime) -> bool:
        return self.pub_date > cmp_date

    def normalize(self):
        # Fix the title
        self.title = strip_html(self.title)

        # Fix the date
        self._pub_date = parse_date(self._pub_date).astimezone(timezone.utc).isoformat()

        # Fix the text
        text = strip_html(self.text)
        text = text.strip()
        text = text.replace("\n", " ")
        text = text.replace("\xa0", " ")
        text = text.split()[:500]
        text = " ".join(text)

        # Add spaces after full stops.
        self.text = re.sub(r"\.(?!\\s)(?!\\d)(?!$)", ". ", self.text)


@dataclasses.dataclass
class PageContent:
    text: str
    favicon_url: str


@dataclasses.dataclass
class Analysis(BaseModel):
    conclusion: str
    summary: str
    subjects: list[str]


@dataclasses.dataclass
class JsonStory:
    uuid: str
    conclusion: str
    summary: str
    subjects: list[str]
    url: str
    favicon: str


class NewsStory:
    uuid: str
    analysis: Analysis
    rss_content: RssContent
    page_content: PageContent

    def __init__(
        self, rss_content: RssContent, page_content: PageContent, analysis: Analysis
    ):
        self.uuid = uuid.uuid4().hex
        self.rss_content = rss_content
        self.page_content = page_content
        self.analysis = analysis

    def to_json(self):
        json_story = JsonStory(
            uuid=self.uuid,
            conclusion=self.analysis.conclusion,
            summary=self.analysis.summary,
            subjects=self.analysis.subjects,
            url=self.rss_content.url,
            favicon=self.page_content.favicon_url,
        )
        return dataclasses.asdict(json_story)


class Newspaper:
    in_queue: Queue
    stories: List[NewsStory]
    out_queue: Queue[NewsStory]
    thread: Thread
    logger: logging.Logger

    def __init__(self) -> None:
        self.logger = logging.getLogger("Newspaper")
        with open("./analyzer_prompt.md") as f:
            self.system_prompt = f.read()

        self.in_queue = Queue()
        self.stories = []
        self.out_queue = Queue()
        self.thread = Thread(target=self.loop)
        self.thread.daemon = True
        self.thread.start()

    def analyze(self, rss_content: RssContent, page_content: PageContent) -> Analysis:
        self.logger.info('Analyzing: "%s"', rss_content.title)
        model = lms.llm()
        chat = lms.Chat(self.system_prompt)

        text = page_content.text
        if not text:
            rss_content.text

        prompt = f"""{rss_content.title}
{text}
"""
        chat.add_user_message(prompt)

        response = model.respond(chat, response_format=Analysis)

        analysis = Analysis.model_validate_json(response.content, strict=True)

        return analysis

    def loop(self):
        while True:
            # Hanging call will wait until new content is received
            self.logger.info("Waiting for news providers...")
            rss_content, page_content = self.in_queue.get()
            analysis = self.analyze(rss_content, page_content)
            story = NewsStory(rss_content, page_content, analysis)
            self.stories.append(story)

            # Push the story to the outgoing queue
            self.out_queue.put(story)


# class Categorizer:
#     system_prompt: str

#     def __init__(self):
#         with open("./categorizer_prompt.md") as f:
#             self.system_prompt = f.read()

#     def get_categories(self, stories: List[NewsStory]) -> List[str]:
#         # Create new categories
#         prompt = ""

#         for story in stories:
#             prompt += f"Article: {story.analysis.conclusion}\n\n"

#         model = lms.llm()
#         chat = lms.Chat(self.system_prompt)
#         chat.add_user_message(prompt)

#         class CategorizeAnswer(BaseModel):
#             categories: List[str]

#         response = model.respond(chat, response_format=CategorizeAnswer)

#         categories = CategorizeAnswer.model_validate_json(
#             response.content, strict=True
#         ).categories

#         logging.info("New Categories: %s", categories)

#         return categories


# @dataclasses.dataclass
# class Node:
#     children: Dict[str, Any]

#     def __getitem__(self, key: str):
#         return self.children[key]

#     def __contains__(self, key: str) -> bool:
#         return key in self.children

#     def add_story(self, story: NewsStory):
#         self.children[story.uuid] = story

#     def add_category(self, category: str):
#         if category in self.children:
#             return
#         self.children[category] = Node({})

#     def remove_stories(self) -> List[NewsStory]:
#         stories = self.stories()
#         for story in stories:
#             del self.children[story.uuid]
#         return stories

#     def stories(self) -> List[NewsStory]:
#         return [v for v in self.children.values() if isinstance(v, NewsStory)]

#     def categories(self) -> Dict[str, Self]:
#         categories = {}
#         for k, v in self.children.items():
#             if isinstance(v, Node):
#                 categories[k] = v
#         return categories

#     def categories_to_json(self) -> dict:
#         categories = {}
#         for category, child in self.categories().items():
#             categories[category] = child.categories_to_json()
#         return categories

#     def to_json(self) -> dict:
#         output = {"subcategories": {}, "stories": []}
#         for key, value in self.children.items():
#             if isinstance(value, NewsStory):
#                 output["stories"].append(value.to_json())
#             elif isinstance(value, Node):
#                 output["subcategories"][key] = value.to_json()
#             else:
#                 raise AssertionError("Unexpeced type in Node child")
#         return output


# class Inserter:
#     system_prompt: str

#     def __init__(self):
#         with open("./inserter_prompt.md") as f:
#             self.system_prompt = f.read()

#     def find_insertion_point(self, root: Node, story: NewsStory) -> Node:
#         node = root
#         if root.categories():
#             logging.info("Consulting smart insert for %s", story.analysis.conclusion)
#             categories_json = root.categories_to_json()
#             categories_str = json.dumps(categories_json)

#             prompt = f"Article: {story.analysis.conclusion}\n\n{categories_str}"

#             model = lms.llm()
#             chat = lms.Chat(self.system_prompt)
#             chat.add_user_message(prompt)

#             class InsertAnswer(BaseModel):
#                 path: List[str]

#             answer = InsertAnswer.model_validate_json(
#                 model.respond(chat, response_format=InsertAnswer).content, strict=True
#             )

#             logging.info("Adding %s to %s", story.analysis.conclusion, answer.path)

#             # Traverse to the correct node
#             for key in answer.path:
#                 if key not in node:
#                     logging.error("Couldn't find node: %s", key)
#                     break
#                 node = node[key]
#         return node

#     def insert(self, root: Node, story: NewsStory):
#         logging.info('Inserting "%s"', story.analysis.conclusion)
#         node = self.find_insertion_point(root, story)

#         # Add the story
#         node.add_story(story)


# class Filter:
#     system_prompt: str

#     def __init__(self):
#         with open("./filter_prompt.md") as f:
#             self.system_prompt = f.read()

#     def matches(self, story: NewsStory, criteria: str) -> bool:
#         logging.info(
#             'Checking if "%s" matches criteria "%s"',
#             story.analysis.conclusion,
#             criteria,
#         )
#         model = lms.llm()
#         chat = lms.Chat(self.system_prompt)

#         prompt = f"""Criteria: {criteria}

# Article: {story.analysis.conclusion} {story.analysis.summary}
# """
#         chat.add_user_message(prompt)

#         class FilterAnswer(BaseModel):
#             include: bool

#         response = model.respond(chat, response_format=FilterAnswer)

#         response = FilterAnswer.model_validate_json(response.content, strict=True)

#         return response.include


# class NewsSession:
#     filter: Filter
#     criteria: str
#     newspaper: Newspaper
#     in_queue: Queue[NewsStory]
#     out_queue: Queue[NewsStory]
#     filtered_stories: List[NewsStory]
#     thread: Thread

#     def __init__(self, newspaper: Newspaper, criteria: str):
#         logging.info("Creating new session with criteria: %s", criteria)
#         self.filter = Filter()
#         self.criteria = criteria
#         self.newspaper = newspaper
#         self.in_queue = Queue()
#         self.out_queue = Queue()

#         # Add all existing stories into our queue
#         for story in self.newspaper.stories:
#             self.in_queue.put(story)

#         # Listen to the newspaper for future updates
#         self.newspaper.out_queues.append(self.in_queue)

#         # Start a thread to process the stories
#         self.thread = Thread(target=self.loop)
#         self.thread.daemon = True
#         self.thread.start()

#     def loop(self):
#         while True:
#             story = self.in_queue.get()
#             if (not self.criteria) or self.filter.matches(story, self.criteria):
#                 logging.info(
#                     'Adding "%s" to "%s"', story.analysis.conclusion, self.criteria
#                 )
#                 self.out_queue.put(story)
