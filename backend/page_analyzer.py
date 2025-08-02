import argparse
import logging

from pymongo import MongoClient
from pymongo.database import Collection
from structs import PageContent, Analysis, LlmAnalysis
import lmstudio as lms
import random
import time
import dataclasses
import json

pipeline = [
    {
        "$lookup": {
            "from": "page_content",
            "localField": "_id",
            "foreignField": "_id",
            "as": "temp1",
        }
    },
    {"$unwind": "$temp1"},
    {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$$ROOT", "$temp1"]}}},
]


class Analyzer:
    metadata_collection: Collection
    analysis_collection: Collection
    model: lms.LLM
    system_prompt: str

    def __init__(
        self, metadata_collection: Collection, analysis_collection: Collection
    ) -> None:
        self.metadata_collection = metadata_collection
        self.analysis_collection = analysis_collection
        self.model = lms.llm()
        with open("./analysis_prompt.md") as f:
            self.system_prompt = f.read()

    def analyze(self, document: dict) -> Analysis:
        title: str = document["title"]
        text: str = document["text"]
        logging.info('Analyzing: "%s"', title)

        prompt = f"""Title: {title}
Content: {text}
"""
        chat = lms.Chat(
            initial_prompt=self.system_prompt,
        )
        chat.add_user_message(prompt)

        response = self.model.respond(chat, response_format=LlmAnalysis)

        llm_analysis = LlmAnalysis.model_validate_json(response.content, strict=True)

        # Remove terms that don't exist in the original text.
        # The AI refuses to follow the rules sometimes.
        llm_analysis.search_terms = set(
            filter(lambda t: t.lower() in text.lower(), llm_analysis.search_terms)
        )

        analysis = Analysis.from_llm_analysis(document["_id"], llm_analysis)

        logging.info("Analysis complete: %s", title)

        return analysis

    def loop(self):
        logging.info("Starting Analysis Loop")
        while True:
            # Analyze page content that's not part of a story
            article_documents = self.metadata_collection.aggregate(pipeline)
            for document in article_documents:
                if self.analysis_collection.find_one({"_id": document["_id"]}):
                    continue

                analysis = self.analyze(document)
                self.analysis_collection.insert_one(dataclasses.asdict(analysis))

            # Sleep for 2 to 5 minutes
            duration = random.randint(60 * 2, 60 * 5)
            logging.info(
                "Sleeping for %d minutes, %d seconds...", duration // 60, duration % 60
            )
            time.sleep(duration)


def main():
    parser = argparse.ArgumentParser(description="Page Analyzer")
    parser.parse_args()

    logging.basicConfig(format="%(asctime)s | %(levelname)-7s | %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client.dolores
    metadata_collection = db.page_metadata
    analysis_collection = db.page_analysis

    analyzer = Analyzer(metadata_collection, analysis_collection)
    analyzer.loop()


if __name__ == "__main__":
    main()
