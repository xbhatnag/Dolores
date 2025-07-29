import argparse
import logging

from pymongo import MongoClient
from pymongo.database import Collection
from structs import PageContent, Analysis, LlmAnalysis
import lmstudio as lms
import random
import time
import dataclasses


class Analyzer:
    page_collection: Collection
    analysis_collection: Collection
    model: lms.LLM
    system_prompt: str

    def __init__(
        self, page_collection: Collection, analysis_collection: Collection
    ) -> None:
        self.page_collection = page_collection
        self.analysis_collection = analysis_collection
        self.model = lms.llm()
        with open("./analysis_prompt.md") as f:
            self.system_prompt = f.read()

    def analyze(self, page_content: PageContent) -> Analysis:
        logging.info('Analyzing: "%s"', page_content.title)

        prompt = f"""{page_content.title}
{page_content.text}
"""
        chat = lms.Chat(
            initial_prompt=self.system_prompt,
        )
        chat.add_user_message(prompt)

        response = self.model.respond(chat, response_format=LlmAnalysis)

        llm_analysis = LlmAnalysis.model_validate_json(response.content, strict=True)

        assert llm_analysis.takeaways, "Takeaways cannot be empty"
        assert llm_analysis.subjects, "Subjects cannot be empty"

        analysis = Analysis.from_llm_analysis(llm_analysis, page_content)

        logging.info("Analysis complete: %s", analysis.title)

        return analysis

    def loop(self):
        logging.info("Starting Analysis Loop")
        while True:
            # Analyze page content that's not part of a story
            for page_content_str in self.page_collection.find():
                page_content = PageContent(**page_content_str)

                if self.analysis_collection.find_one({"_id": page_content._id}):
                    break

                analysis = self.analyze(page_content)
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
    page_collection = db.pages
    analysis_collection = db.analyses

    analyzer = Analyzer(page_collection, analysis_collection)
    analyzer.loop()


if __name__ == "__main__":
    main()
