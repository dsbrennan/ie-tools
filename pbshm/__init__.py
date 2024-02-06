import importlib
import importlib.util
import json
import os
import site
import sys

from flask import Flask

def create_app(test_config=None):
    #Create Flask App
    app = Flask(__name__, instance_relative_config=True)

    #Load Configuration
    app.config.from_mapping(
        PAGE_SUFFIX=" - PBSHM Debug & Development",
        LOGIN_MESSAGE="PBSHM Debug & Development Mode: Enter your authentication credentials below.",
        FOOTER_MESSAGE="PBSHM Debug & Development - PBSHM IE Toolbox",
        NAVIGATION={
            "modules":{
                "IE Tools" : "ie-tools.list_models",
                "Help": "layout.home"
            }
        }
    )
    app.config.from_file("config.json", load=json.load, silent=True) if test_config is None else app.config.from_mapping(test_config)

    #Ensure Instance Folder
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    #Include PBSHM Core Packages
    importlib.invalidate_caches()
    pbshm_directory = os.path.join(site.getsitepackages()[0], "pbshm")
    pbshm_modules = {
        "pbshm.db": {
            "path": ["db.py"],
            "blueprint": False,
            "url_prefix": None
        },
        "pbshm.mechanic": {
            "path": ["mechanic", "__init__.py"],
            "blueprint": True,
            "url_prefix": None
        },
        "pbshm.initialisation": {
            "path": ["initialisation", "__init__.py"],
            "blueprint": True,
            "url_prefix": None
        },
        "pbshm.authentication": {
            "path": ["authentication", "__init__.py"],
            "blueprint": True,
            "url_prefix": "/authentication"
        },
        "pbshm.layout": {
            "path": ["layout", "__init__.py"],
            "blueprint": True,
            "url_prefix": "/layout"
        },
        "pbshm.timekeeper": {
            "path": ["timekeeper", "__init__.py"],
            "blueprint": True,
            "url_prefix": "/timekeeper"
        }
    }
    for module_name in pbshm_modules:
        print(f"Loading PBSHM Module: {module_name}")
        module_spec = importlib.util.spec_from_file_location(module_name, os.path.join(pbshm_directory, *pbshm_modules[module_name]["path"]))
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        if pbshm_modules[module_name]["blueprint"]:
            app.register_blueprint(module.bp, url_prefix=pbshm_modules[module_name]["url_prefix"])

    #Include Developing Module: IE Tools
    from pbshm import ietools # Note: Must be done after the core modules are loaded in otherwise any references to core modules will fail
    app.register_blueprint(ietools.bp, url_prefix="/toolbox/ie")
    
    #Set Root Page
    app.add_url_rule("/", endpoint="ie-tools.list_models")

    #Return App
    return app