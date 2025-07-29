import argparse
import logging

from pymongo import MongoClient
from pymongo.database import Collection
from structs import Analysis


class StoryAggregator:
    analysis_collection: Collection

    def __init__(self, analysis_collection: Collection) -> None:
        self.analysis_collection = analysis_collection

    def loop(self):
        logging.info("Starting Aggregator Loop")
        while True:
            # Sleep for 2 to 5 minutes
            # duration = random.randint(60 * 2, 60 * 5)
            # logging.info(
            #     "Sleeping for %d minutes, %d seconds...", duration // 60, duration % 60
            # )
            # time.sleep(duration)

            # Analyze page content that's not part of a story
            for this_analysis_struct in self.analysis_collection.find():
                this_analysis = Analysis(**this_analysis_struct)

                common_subjects_article_dict = {}

                for other_analysis_Struct in self.analysis_collection.find():
                    other_analysis = Analysis(**other_analysis_Struct)

                    if this_analysis._id == other_analysis._id:
                        continue

                    this_subjects = set(this_analysis.subjects)
                    other_subjects = set(other_analysis.subjects)

                    common_subjects = this_subjects.intersection(other_subjects)
                    common_subjects_article_dict[other_analysis._id] = common_subjects

                    if common_subjects:
                        logging.info(
                            "[%s + %s] = %s",
                            this_analysis.takeaways[0],
                            other_analysis.takeaways[0],
                            common_subjects,
                        )


def main():
    parser = argparse.ArgumentParser(description="Story Aggregator")
    parser.parse_args()

    logging.basicConfig(format="%(asctime)s | %(levelname)-7s | %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client.dolores
    page_collection = db.pages
    analysis_collection = db.analyses

    analyzer = StoryAggregator(analysis_collection)
    analyzer.loop()


if __name__ == "__main__":
    main()
