# PBSHM IE Toolkit
The PBSHM IE Toolkit is designed to help users interact and design IE models for use within the [PBSHM Core](https://github.com/dynamics-research-group/pbshm-flask-core). The toolkit enables IE models to be either created within the online text editor or upload existing [PBSHM Schema](https://github.com/dynamics-research-group/pbshm-schema) compliant JSON files.

Each IE model is placed within a private users sandbox, each model then goes through two steps of varification. Step 1: Validate the syntax of the IE model against the latest version of the [PBSHM Schema](https://github.com/dynamics-research-group/pbshm-schema). Step 2: Validate that the logic of the IE model holds true (e.g if a grounded model, there should be at least one ground element).

Once a model has passed both stages of validation, this model can then be included in the global IE model catalogue of the system.

For more information about the syntax of an IE model, please read the documentation for the [PBSHM Schema](https://github.com/dynamics-research-group/pbshm-schema).

## Installation
Install the package via pip:
```
pip install pbshm-ie-toolbox
```

## Setup
Firstly, configure the PBSHM Core by following the [outlined guide](https://github.com/dynamics-research-group/pbshm-flask-core#setup)

## Running
The application is run via the standard Flask command:
```
flask run
```

## File size issue
If you get an error when uploading a large IE model, you can add the following line of code into your `pbshm` `__init__.py` file:
```
# Change max content size to 16MB
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000
```