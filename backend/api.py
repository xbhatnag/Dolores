from pymongo import MongoClient
from pymongo.database import Collection
from flask import Flask, jsonify, make_response
import logging

app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["dolores"]
metadata_collection: Collection = db["page_metadata"]
content_collection: Collection = db["page_content"]
analysis_collection: Collection = db["page_analysis"]


# Add CORS headers to every response
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    return response


@app.route("/all", methods=["GET"])
def get_all():
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
        {
            "$lookup": {
                "from": "page_analysis",
                "localField": "_id",
                "foreignField": "_id",
                "as": "temp2",
            }
        },
        {"$unwind": "$temp2"},
        {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$$ROOT", "$temp2"]}}},
        {"$project": {"temp1": 0, "temp2": 0}},
    ]

    results = list(metadata_collection.aggregate(pipeline))
    return make_response(jsonify(results))


@app.route("/clear", methods=["POST"])
def clear_all():
    result = analysis_collection.delete_many({})
    logging.info("Deleted %d analysis documents", result.deleted_count)
    result = content_collection.delete_many({})
    logging.info("Deleted %d content documents", result.deleted_count)
    result = metadata_collection.delete_many({})
    logging.info("Deleted %d metadata documents", result.deleted_count)
    return make_response(jsonify({}))


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s | %(levelname)-7s | %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    app.run(host="0.0.0.0", port=3000, debug=True)
