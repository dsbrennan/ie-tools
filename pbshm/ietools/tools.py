from flask import g, current_app
from pbshm.db import db_connect
from pbshm.mechanic.mechanic import create_new_structure_collection
from typing import Tuple
import json
import pymongo.errors
import bson.objectid
import pymongo.collection

def sandbox_collection_name(user_id: str, validation: bool) -> str:
    return f"sandbox-validation-{user_id}" if validation else f"sandbox-free-{user_id}"

def ensure_sandbox_collection(user_id: str, validation: bool):
    collection_name = sandbox_collection_name(user_id, validation)
    collection_count = 0
    for _ in db_connect().list_collection_names(filter={"name": collection_name}):
        collection_count += 1
    if collection_count == 0:
        if validation:
            create_new_structure_collection(collection_name)
        else:
            db_connect().create_collection(collection_name)
            db_connect()[collection_name].create_index([
                ("population", pymongo.ASCENDING),
                ("name", pymongo.ASCENDING),
                ("timestamp", pymongo.ASCENDING)
            ], name="pbshm_framework_structure", unique=True)

def ensure_sandbox_setup():
    # Setup Collections
    if g is None or g.user is None or "_id" not in g.user:
        raise Exception("Sorry, you must be logged in")
    else:
        ensure_sandbox_collection(g.user["_id"], validation=True)
        ensure_sandbox_collection(g.user["_id"], validation=False)

def sandbox_collection(validation: bool) -> pymongo.collection.Collection:
    return db_connect()[sandbox_collection_name(g.user["_id"], validation)]

def load_default_json() -> object:
    json_object = {}
    with current_app.open_resource("ietools/files/blank-structure.json") as file:
        json_object = json.load(file)
    return json_object

def validate_json(json_str: str) -> Tuple[bool, str, object]:
    json_object = {}
    try:
        json_object = json.loads(json_str)
    except ValueError as err:
        return False, err, {}
    return True, "", json_object

def insert_staging_document(document: object) -> Tuple[str, str]:
    errors, id = "", ""
    try:
        result = sandbox_collection(False).insert_one(document)
        if result.inserted_id is None:
            errors += "Unable to insert document into the database"
        else:
            id = result.inserted_id
    except pymongo.errors.DuplicateKeyError as duplicateErr:
        errors += "There is already an IE model in the database with the same name, population and timestamp"
    return errors, id

def update_staging_document(id: str, document: object) -> Tuple[str, str]:
    errors = ""
    try:
        result = sandbox_collection(False).replace_one(
            {"_id": bson.objectid.ObjectId(id)}, document
        )
        if result.matched_count < 1:
            errors += "Unable to find document to replace within the database"
        elif result.modified_count < 1:
            errors += "Unable to replace document within the database"
    except pymongo.errors.PyMongoError:
        errors += "Unable to update the document (generic error)"
    return errors, id