import dataclasses
from typing import List
from tts import generate_audio, random_narrator

import re
import bs4
from threading import Lock, Thread

from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from pydantic import BaseModel
from queue import Queue
import google.genai
import google.genai.types

import logging
import json
import uuid


def strip_html(html: str) -> str:
    # Remove HTML tags and decode HTML entities
    soup = bs4.BeautifulSoup(html, features="html.parser")
    text = soup.get_text()
    return text.strip()


@dataclasses.dataclass
class WrittenContent:
    source: str
    title: str
    type: str
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
        self.text = re.sub(r"\.(?!\\s)(?!\\d)(?!$)", ". ", text)


@dataclasses.dataclass
class Analysis(BaseModel):
    conclusion: str
    summary: str
    feelings: str


class NewsStory:
    uuid: str
    analysis: Analysis
    content: WrittenContent

    def __init__(self, content: WrittenContent, analysis: Analysis):
        self.uuid = uuid.uuid4().hex
        self.content = content
        self.analysis = analysis


class Analyzer:
    def __init__(self):
        with open("./analyzer_prompt.md") as f:
            system_prompt = f.read()

        tools = []
        # tools.append(types.Tool(url_context=types.UrlContext))
        # tools.append(google.genai.types.Tool(google_search=google.genai.types.GoogleSearch))
        self.chat = google.genai.Client(
            vertexai=True,
            project="dolores-cb057",
            location="us-west1",
            http_options=google.genai.types.HttpOptions(api_version="v1"),
        ).chats.create(
            model="gemini-2.5-pro",
            config=google.genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools,
                response_mime_type="application/json",
                response_schema=Analysis,
            ),
        )

    def analyze(self, content: WrittenContent):
        logging.info("Analyzing \"%s\"...", content.title)
        response = self.chat.send_message(
            message=f"""{content.title}

{content.tags}

{content.text}
"""
        )

        assert isinstance(response.parsed, Analysis)

        return response.parsed


@dataclasses.dataclass
class ApiStory:
    uuid: str
    conclusion: str
    summary: str
    feelings: str
    url: str

    def __init__(self, story: NewsStory):
        self.uuid = story.uuid
        self.conclusion = story.analysis.conclusion
        self.summary = story.analysis.summary
        self.feelings = story.analysis.feelings
        self.url = story.content.url

def create_gemini_category_tree(level):
    if level["subcategories"]:
        new_tree = {}
        for key in level["subcategories"]:
            new_tree[key] = create_gemini_category_tree(level["subcategories"][key])
        return new_tree
    return {}

def insert(story: NewsStory, root: dict, path: List[str]):
    node: dict = root
    logging.info(f"Inserting {story.analysis.conclusion} at {path}")
    for key in path:
        if key not in node["subcategories"]:
            node["subcategories"][key] = {
                "subcategories": {},
                "stories": []
            }
        node = node["subcategories"][key]
    node["stories"].append(dataclasses.asdict(ApiStory(story)))

class Categorizer:
    tree: dict

    def __init__(self):
        self.tree = {
            "subcategories": {},
            "stories": []
        }
        with open("./categorizer_prompt.md") as f:
            system_prompt = f.read()

        tools = []
        # tools.append(types.Tool(url_context=types.UrlContext))
        # tools.append(google.genai.types.Tool(google_search=google.genai.types.GoogleSearch))
        self.chat = google.genai.Client(
            vertexai=True,
            project="dolores-cb057",
            location="us-west1",
            http_options=google.genai.types.HttpOptions(api_version="v1"),
        ).chats.create(
            model="gemini-2.5-flash",
            config=google.genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools,
                response_mime_type="application/json",
            ),
        )


    def categorize(self, story: NewsStory):
        logging.info("Categorizing \"%s\"", story.analysis.conclusion)
        tree = create_gemini_category_tree(self.tree)
        tree_str = json.dumps(tree)

        response = self.chat.send_message(
            message=f"""{story.analysis.conclusion}
{story.analysis.summary}
-------------------
{tree_str}
"""
        )

        assert response.text
        path = json.loads(response.text)

        assert isinstance(path, list)
        
        insert(story, self.tree, path)


class NewsStories:
    story_list: List[NewsStory]
    lock: Lock
    content_queue: Queue[WrittenContent]
    analyzer: Analyzer
    categorizer: Categorizer

    def __init__(self) -> None:
        self.story_list = []
        self.analyzer = Analyzer()
        self.categorizer = Categorizer()
        self.content_queue = Queue()
        self.lock = Lock()
        pass

    def tree(self) -> dict:
        return self.categorizer.tree

    def next(self) -> dict:
        # Hanging call will wait until a new story is received
        # and analyzed
        content: WrittenContent = self.content_queue.get()
        analysis = self.analyzer.analyze(content)
        story = NewsStory(content, analysis)
        self.categorizer.categorize(story)
        with self.lock:
            self.story_list.append(story)
        return self.categorizer.tree

    def queue(self) -> Queue[WrittenContent]:
        return self.content_queue

    def get(self, uuid: str) -> NewsStory | None:
        with self.lock:
            return next(
                (story for story in self.story_list if story.uuid == uuid), None
            )
