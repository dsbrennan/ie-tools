import json

import bson.objectid
from flask import Blueprint, request, render_template, url_for, redirect

from pbshm.authentication import authenticate_request
from pbshm.timekeeper import nanoseconds_since_epoch_to_datetime

from pbshm.ietools.tools import ensure_sandbox_setup, sandbox_collection, load_default_json, validate_json, validate_basic_document_structure, insert_staging_document, update_staging_document, validate_model_syntax, validate_model_logic, include_validated_model

# Create the tools blueprint
bp = Blueprint(
    "ie-tools", 
    __name__, 
    template_folder="templates"
)

# List Route
@bp.route("/", methods=("GET", "POST"))
@authenticate_request("ie-tools-list")
def list_models():
    # Ensure Setup
    ensure_sandbox_setup()
    # Upload
    errors = ""
    if request.method == "POST":
        if "model" not in request.files:
            errors += "No upload found"
        else:
            file = request.files["model"]
            if file.filename.strip() == '':
                errors += "No file selected"
            elif file.filename.rsplit('.', 1)[1].lower() != 'json':
                errors += "This upload only accepts json files"
            else:
                validated_json = validate_json(file.read())
                if not validated_json[0]:
                    errors += f"Was unable to save the IE Model as it was not valid JSON: {validated_json[1]}"
                else:
                    model = validated_json[2]
                    validated_basic_syntax = validate_basic_document_structure(model)
                    if not validated_basic_syntax[0]:
                        errors += validated_basic_syntax[1]
                    else:
                        model_errors, model_id = insert_staging_document(model)
                        if len(model_errors) > 0:
                            errors += model_errors
                        elif model_id is not None:
                            return redirect(url_for(f"{bp.name}.validate_model", population=model["population"], name=model["name"], timestamp=model["timestamp"]))

    # Load Models
    models = []
    for document in sandbox_collection(False).find():
        models.append({
            "id": document["_id"],
            "name": document["name"],
            "population": document["population"],
            "timestamp": document["timestamp"],
            "date": nanoseconds_since_epoch_to_datetime(document["timestamp"]).strftime("%d/%m/%Y %H:%M:%S"),
            "elements": len(document["models"]["irreducibleElement"]["elements"]) if "models" in document and "irreducibleElement" in document["models"] and "elements" in document["models"]["irreducibleElement"] else 0,
            "relationships": len(document["models"]["irreducibleElement"]["relationships"]) if "models" in document and "irreducibleElement" in document["models"] and "relationships" in document["models"]["irreducibleElement"] else 0
        })
    # Render
    return render_template("list-models.html", errors=errors, models=models)

# Edit Route
@bp.route("/sandbox/edit", defaults={"id": None}, methods=("GET", "POST"))
@bp.route("/sandbox/<id>/edit", methods=("GET", "POST"))
@authenticate_request("ie-tools-edit")
def edit_model(id):
    ensure_sandbox_setup()
    name, errors, model = "", "", None
    if id is None:
        name = "Create a new IE Model"
        model = load_default_json()
    if request.method == "GET":
        if id is not None:
            for document in sandbox_collection(False).find({"_id": bson.objectid.ObjectId(id)}, {"_id": 0}).limit(1):
                name = f"{document['population']}, {document['name']}, {nanoseconds_since_epoch_to_datetime(document['timestamp']).strftime('%d/%m/%Y %H:%M:%S')}"
                model = document
                break
    elif request.method == "POST":
        if "ie-model-json" not in request.form or len(request.form["ie-model-json"].strip()) == 0:
            errors += "Please enter the IE Model"
        else:
            validated_json = validate_json(request.form["ie-model-json"])
            if not validated_json[0]:
                errors += f"Was unable to save the IE Model as it was not valid JSON: {validated_json[1]}"
            else:
                model = validated_json[2]
                validated_basic_syntax = validate_basic_document_structure(model)
                if not validated_basic_syntax[0]:
                    errors += validated_basic_syntax[1]
                else:
                    model_errors, model_id = update_staging_document(id, model) if id is not None else insert_staging_document(model)
                    if len(model_errors) > 0:
                        errors += model_errors
                    elif id is None and model_id is not None:
                        return redirect(url_for(f"{bp.name}.edit_model", id=model_id))
                    elif id is not None:
                        name = f"{validated_json[2]['population']}, {validated_json[2]['name']}, {nanoseconds_since_epoch_to_datetime(validated_json[2]['timestamp']).strftime('%d/%m/%Y %H:%M:%S')}"
    
    return render_template(
        "edit-model.html", 
        id=id, 
        name=name, 
        errors=errors, 
        model=json.dumps(model, indent=4) if model is not None else request.form["ie-model-json"]
    )

@bp.route("/sandbox/<population>/<name>/<int:timestamp>/validate")
@authenticate_request("ie-tools-validate")
def validate_model(population: str, name: str, timestamp: int):
    return render_template("validate-model.html", name=name, population=population, timestamp=timestamp)

@bp.route("/sandbox/<population>/<name>/<int:timestamp>/include")
@authenticate_request("ie-tools-include")
def include_model(population: str, name: str, timestamp: int):
    validation = include_validated_model(name, population, timestamp)
    return {"validated": validation}

@bp.route("/sandbox/<population>/<name>/<int:timestamp>/validate-syntax")
@authenticate_request("ie-tools-validate-syntax")
def validate_syntax(population: str, name: str, timestamp: int):
    validation = validate_model_syntax(name, population, timestamp)
    return {"validated": validation[0], "details": validation[1]}

@bp.route("/sandbox/<population>/<name>/<int:timestamp>/validate-logic")
@authenticate_request("ie-tools-validate-logic")
def validate_logic(population: str, name: str, timestamp: int):
    validation = validate_model_logic(name, population, timestamp)
    return {"validated": validation[0], "details": validation[1]}
