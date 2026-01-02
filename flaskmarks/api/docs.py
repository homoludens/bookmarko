"""
API documentation with Swagger UI.

Provides interactive API documentation using OpenAPI/Swagger specification.
"""
from __future__ import annotations

import os

from flask import Blueprint, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint

# Path to the OpenAPI spec file
OPENAPI_SPEC_PATH = os.path.join(os.path.dirname(__file__), 'openapi.yaml')

# Swagger UI configuration
SWAGGER_URL = '/api/docs'
API_SPEC_URL = '/api/v1/openapi.yaml'

# Create Swagger UI blueprint
swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_SPEC_URL,
    config={
        'app_name': 'Bookmarko API',
        'docExpansion': 'list',
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'tryItOutEnabled': True,
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'filter': True,
        'syntaxHighlight': {
            'activate': True,
            'theme': 'monokai'
        }
    }
)

# Blueprint to serve the OpenAPI spec file
api_spec = Blueprint('api_spec', __name__, url_prefix='/api/v1')


@api_spec.route('/openapi.yaml')
def serve_openapi_spec():
    """Serve the OpenAPI specification file."""
    return send_from_directory(
        os.path.dirname(__file__),
        'openapi.yaml',
        mimetype='application/x-yaml'
    )


@api_spec.route('/openapi.json')
def serve_openapi_spec_json():
    """Serve the OpenAPI specification as JSON."""
    import yaml
    from flask import jsonify
    
    with open(OPENAPI_SPEC_PATH, 'r') as f:
        spec = yaml.safe_load(f)
    
    return jsonify(spec)
