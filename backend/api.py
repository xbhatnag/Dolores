from pymongo import MongoClient
from pymongo.database import Collection
from flask import Flask, jsonify, make_response


app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["dolores"]
collection: Collection = db["analyses"]


# Add CORS headers to every response
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    return response


@app.route("/all", methods=["GET"])
def get_analyses():
    return make_response(jsonify(list(collection.find())))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
