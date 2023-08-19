# Irreducible Element model tools
The Irreducible Element (IE) model toolkit is designed to help users interact and design IE models for use within the [PBSHM Flask Core](https://github.com/dynamics-research-group/pbshm-flask-core). The toolkit enables IE models to be either created within the online text editor or upload existing [PBSHM Schema](https://github.com/dynamics-research-group/pbshm-schema) compliant JSON files.

Each IE model is placed within a private users sandbox, each model then goes through two steps of varification. Step 1: Validate the syntax of the IE model against the latest version of the [PBSHM Schema](https://github.com/dynamics-research-group/pbshm-schema). Step 2: Validate that the logic of the IE model holds true (e.g if a grounded model, there should be at least one ground element).

Once a model has passed both stages of validation, this model can then be included in the global IE model catalogue of the system.

For more information about the syntax of an IE model, please read the documentation for the [PBSHM Schema](https://github.com/dynamics-research-group/pbshm-schema).

## Installation
First, install the PBSHM Flask Core as outlined [here](https://github.com/dynamics-research-group/pbshm-flask-core#installation).

Once the PBSHM Flask core is installed and setup, copy the `ietools` folder from this repository into the `pbshm` root folder within the PBSHM Flask Core setup on your workstation. Once this is done, you then need to modify the __init__.py file within the `pbshm` root folder (in the working version of PBSHM Flask Core on your workstation), to include the following code:
```
## IE Tools
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000#16MB
from pbshm.ietools import routes
app.register_blueprint(routes.bp, url_prefix="/ie-tools")
```
The above code, should go below the lines where the Pathfinder blueprint is added.
