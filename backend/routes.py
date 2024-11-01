from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health")
def the_health():
    return jsonify(dict(status="OK")), 200

@app.route("/count")
def the_count():
    count = db.songs.count_documents({})

    return {"count": count}, 200

@app.route("/song")
def songs():
    results = list(db.songs.find({}))
    
    return {"songs": parse_json(results)}, 200

@app.route("/song/<id>")
def get_song_by_id(id):
    results = db.songs.find_one({"id": id})
    
    if not results:
        return {"message": f"song with id {id} not found"}, 404
        
    return parse_json(results), 200

@app.route("/song", methods=["POST"])
def create_song():
    # Retrieve JSON data from the request
    song_in = request.json

    # Check if a song with the given ID already exists
    if db.songs.find_one({"id": song_in["id"]}):
        return {"Message": f"Song with id {song_in['id']} already exists"}, 302

    # Insert the new song and return the inserted ID
    insert_id = db.songs.insert_one(song_in).inserted_id
    return {"inserted_id": parse_json(insert_id)}, 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    # Get data from the JSON body
    song_in = request.json

    # Check if the song with the given ID exists
    song = db.songs.find_one({"id": id})

    if song is None:
        return {"message": "song not found"}, 404

    # Prepare the updated data
    updated_data = {"$set": song_in}

    # Update the song with the new data
    result = db.songs.update_one({"id": id}, updated_data)

    # Check if anything was modified
    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}, 200
    else:
        # Return the updated song details
        return parse_json(db.songs.find_one({"id": id})), 201

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    result = db.songs.delete_one({"id": id})

    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    else:
        return "", 204