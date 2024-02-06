import json
from typing import Tuple

import bson.objectid
import pymongo
import pymongo.collection
import pymongo.errors
from flask import g, current_app

from pbshm.db import db_connect
from pbshm.mechanic import create_new_structure_collection

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

def validate_basic_document_structure(document: object) -> Tuple[bool, str]:
    errors = ""
    if "name" not in document:
        errors += f"You must have a structure name before you can save it into the system"
    elif "population" not in document:
        errors += f"You must have a population before you can save it into the system"
    elif "timestamp" not in document:
        errors += f"You must have a timestamp before you can save it into the system"
    elif "models" not in document:
        errors += f"You must have declared a model before you can save into into the system"
    elif "irreducibleElement" not in document["models"]:
        errors += f"You must have declared a irreducible element model before you can save into into the system"
    return True if len(errors) == 0 else False, errors

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

def validate_model_syntax(name: str, population: str, timestamp: int) -> Tuple[bool, object]:
    sandbox_collection(True).delete_many({
        "$and":[
            {"name": name},
            {"population": population},
            {"timestamp": timestamp}
        ]
    })
    try:
        sandbox_collection(False).aggregate([
            {"$match":{
                "name": name,
                "population": population,
                "timestamp": timestamp
            }},
            {"$project":{
                "_id": 0
            }},
            {"$merge": sandbox_collection_name(g.user["_id"], True)}
        ])
        return True, None
    except pymongo.errors.OperationFailure as err:
        error = {}
        if err.details["code"] == 121:
            error["reason"] = "Document failed PBSHM Schema validation"
            error["document"] = str(err.details["errInfo"]["failingDocumentId"])
            error["cause"] = err.details["errInfo"]["details"]["schemaRulesNotSatisfied"]
        return False, error

def model_logic_error(type:str, objects: list, documents: list, description: str) -> object:
    return {
        "type": type,
        "objects": objects,
        "documents": documents,
        "description": description
    }

def validate_model_logic(name: str, population: str, timestamp: int) -> Tuple[bool, object]:
    model_type, model_type_document_id = "", ""
    errors, elements, relationships = [], [], []
    element_documents, relationship_documents = [], []
    for document in sandbox_collection(True).find({
        "$and":[
            {"name": name},
            {"population": population},
            {"timestamp": timestamp}
        ]
    }):
        id = str(document["_id"])
        model = document["models"]["irreducibleElement"]
        type = model["type"]
        # Type
        if model_type == "":
            model_type = type
            model_type_document_id = id
        elif model_type != type:
            errors.append(model_logic_error(
                "conflicting model types",
                [model_type, type],
                [model_type_document_id, id],
                f"The first document in the model declares the type as a {model_type}, however, {id} declares it as a {type}"
            ))
        # Unique elements
        for element in model["elements"]:
            name = element["name"]
            for existing in element_documents:
                if existing[0] == name:
                    errors.append(model_logic_error(
                        "duplicate element",
                        [name],
                        [id, existing[1]],
                        f"The element {name} is declared in {id} as well as being declared in {existing[1]}"
                    ))
                    break
            elements.append(element)
            element_documents.append((name, id))
        # Unique relationships
        for relationship in model["relationships"]:
            name = relationship["name"]
            for existing in relationship_documents:
                if existing[0] == name:
                    errors.append(model_logic_error(
                        "duplicate relationship",
                        [name],
                        [id, existing[1]],
                        f"The relationship {name} is declared in {id} as well as being declared in {existing[1]}"
                    ))
                    break
            relationships.append(relationship)
            relationship_documents.append((name, id))
    # Model type requirements
    if model_type == "grounded":
        ground_element_count = 0
        for element in elements:
            if element["type"] == "ground":
                ground_element_count += 1
                break
        if ground_element_count == 0:
            errors.append(model_logic_error(
                "missing ground",
                [model_type],
                [],
                f"The model is declared as a {model_type} model, however, it has no ground elements"
            ))
    # Relationship elements
    elements_used = []
    for relationship in relationships:
        id, name = "", relationship["name"]
        for source in relationship_documents:
            if name == source[0]:
                id = source[1]
                break
        for relationship_element in relationship["elements"]:
            relationship_element_name = relationship_element["name"]
            element_exists = False
            for element in elements:
                if relationship_element_name == element["name"]:
                    element_exists = True
                    break
            if not element_exists:
                errors.append(model_logic_error(
                    "missing element",
                    [name, relationship_element_name],
                    [id],
                    f"The relationship {name} declared in {id} uses the element {relationship_element_name}, however, it doesn't exist within the model"
                ))
            else:
                elements_used.append(relationship_element_name)
    # Orphaned elements
    for element in elements:
        name = element["name"]
        if name not in elements_used:
            id = ""
            for source in element_documents:
                if name == source[0]:
                    id = source[1]
                    break
            errors.append(model_logic_error(
                "orphaned element",
                [name],
                [id],
                f"The element {name} is declared in {id}, however, it is never used within a relationship"
            ))
    return True if len(errors) == 0 else False, errors

def include_validated_model(name: str, population: str, timestamp: int) -> bool:
    validated = validate_model_syntax(name, population, timestamp)
    if not validated[0]:
        return False
    validated = validate_model_logic(name, population, timestamp)
    if not validated[0]:
        return False
    sandbox_collection(True).aggregate([
        {"$match":{
            "$and":[
                {"name": name},
                {"population": population},
                {"timestamp": timestamp}
            ]
        }},
        {"$project":{
            "_id": 0
        }},
        {"$merge": current_app.config["DEFAULT_COLLECTION"]}
    ])
    return True