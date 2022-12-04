from flask import Blueprint, request, render_template, url_for, redirect
from pbshm.authentication.authentication import authenticate_request
from pbshm.ietools.tools import ensure_sandbox_setup, sandbox_collection, load_default_json, validate_json, insert_staging_document, update_staging_document
from pbshm.pathfinder.pathfinder import nanoseconds_since_epoch_to_datetime
import json
import bson.objectid

# Create the tools blueprint
bp = Blueprint(
    "ie-tools", 
    __name__, 
    template_folder="templates"
)

# List Route
@bp.route("/")
@authenticate_request("ie-tools-list")
def list_models():
    # Ensure Setup
    ensure_sandbox_setup()
    models = []
    for document in sandbox_collection(False).find():
        models.append({
            "id":document["_id"],
            "name":document["name"],
            "population":document["population"],
            "date":nanoseconds_since_epoch_to_datetime(document["timestamp"]),
            "elements":len(document["models"]["irreducibleElement"]["elements"]) if "models" in document and "irreducibleElement" in document["models"] and "elements" in document["models"]["irreducibleElement"] else 0,
            "relationships":len(document["models"]["irreducibleElement"]["relationships"]) if "models" in document and "irreducibleElement" in document["models"] and "relationships" in document["models"]["irreducibleElement"] else 0
        })
    # Render
    return render_template("list-models.html", models=models)

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
                name = f"{document['population']}, {document['name']}, {document['timestamp']}"
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
                if "name" not in validated_json[2]:
                    errors += f"You must have a structure name before you can save it into the system"
                elif "population" not in validated_json[2]:
                    errors += f"You must have a population before you can save it into the system"
                elif "timestamp" not in validated_json[2]:
                    errors += f"You must have a timestamp before you can save it into the system"
                elif "models" not in validated_json[2]:
                    errors += f"You must have declared a model before you can save into into the system"
                elif "irreducibleElement" not in validated_json[2]["models"]:
                    errors += f"You must have declared a irreducible element model before you can save into into the system"
                else:
                    model_errors, model_id = update_staging_document(id, model) if id is not None else insert_staging_document(model)
                    if len(model_errors) > 0:
                        errors += model_errors
                    elif id is None and model_id is not None:
                        return redirect(url_for(f"{bp.name}.edit_model", id=model_id))
                    elif id is not None:
                        name = f"{validated_json[2]['population']}, {validated_json[2]['name']}, {validated_json[2]['timestamp']}"
    
    return render_template(
        "edit-model.html", 
        id=id, 
        name=name, 
        errors=errors, 
        model=json.dumps(model, indent=4) if model is not None else request.form["ie-model-json"]
    )