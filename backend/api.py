from pymongo import MongoClient
from pymongo.database import Collection
from flask import Flask, jsonify, make_response


app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["dolores"]
metadata_collection: Collection = db["page_metadata"]


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
