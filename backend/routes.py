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

@app.route("/health", methods=["GET"])
def get_health():
    """return the health status of the server"""
    return {"status":"OK"}

@app.route("/count", methods=["GET"])
def count():
    """returns the number of songs in the database"""
    count = db.songs.count_documents({})
    return {"count": count}, 200

@app.route("/song", methods=["GET"])
def songs():
    """returns all songs"""
    songs_cursor = db.songs.find({})
    list_cursor = list(songs_cursor)
    json_songs = parse_json(list_cursor)
    return {"songs": json_songs}, 200

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """returns a song's info by its id"""
    found_song = parse_json(db.songs.find_one({"id": id}))
    print(found_song)
    if found_song:
        return found_song, 200
    return {"message": "song with id not found"}, 404

@app.route("/song", methods=["POST"])
def create_song():
    """posts a song to the db via req json"""
    song_data = request.json
    found_song = parse_json(db.songs.find_one({"id": song_data["id"]}))
    if found_song:
        return {"Message": f"song with id {song_data['id']} already present"}
    res = db.songs.insert_one(song_data)
    _id = str(res.inserted_id)
    return {"inserted_id": {"$oid": _id}}, 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """updates a song in the db by id"""
    song_data = request.json
    found_song = parse_json(db.songs.find_one({"id": id}))
    if found_song:
        newvalues = { "$set": song_data }
        res = db.songs.update_one({"id": id}, newvalues)
        if res.modified_count == 0:
            return {"message":"song found, but nothing updated"}, 200
        return parse_json(db.songs.find_one({"id": id})), 201
    return {"message": "song not found"}, 404

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """deletes a song by id"""
    res = db.songs.delete_one({"id": id})
    if res.deleted_count == 0:
        return {"message": "song not found"}, 404
    return "", 204
