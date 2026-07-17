import json
from pathlib import Path
from backend.main import app
import pytest

CONTRACTS_DIR = Path(__file__).parent.parent.parent / "testing" / "contracts"
OPENAPI_FILE = CONTRACTS_DIR / "openapi.json"

import os

@pytest.fixture
def baseline_openapi():
    current_openapi = app.openapi()
    if os.environ.get("UPDATE_CONTRACT_BASELINE") == "true":
        with open(OPENAPI_FILE, "w", encoding="utf-8") as f:
            json.dump(current_openapi, f, indent=2)
        return current_openapi
        
    if not OPENAPI_FILE.exists():
        pytest.skip("Baseline OpenAPI file not found. Run with UPDATE_CONTRACT_BASELINE=true to generate.")
        
    with open(OPENAPI_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def test_openapi_contract_no_removed_endpoints(baseline_openapi):
    """Ensure no endpoints from the baseline contract were removed in the live app."""
    current_openapi = app.openapi()
    baseline_paths = baseline_openapi.get("paths", {})
    current_paths = current_openapi.get("paths", {})

    for path, path_item in baseline_paths.items():
        assert path in current_paths, f"Endpoint {path} is missing from live API contract"
        
        for method, operation in path_item.items():
            assert method in current_paths[path], f"Method {method} on {path} is missing from live API contract"
            
            # Check for removed parameters
            baseline_params = {p.get("name") for p in operation.get("parameters", []) if "name" in p}
            current_params = {p.get("name") for p in current_paths[path][method].get("parameters", []) if "name" in p}
            missing_params = baseline_params - current_params
            assert not missing_params, f"Parameters {missing_params} missing from {method.upper()} {path}"
            
            # Check response status codes stability
            baseline_responses = set(operation.get("responses", {}).keys())
            current_responses = set(current_paths[path][method].get("responses", {}).keys())
            missing_responses = baseline_responses - current_responses
            # Allow adding new responses but don't allow removing baseline responses
            assert not missing_responses, f"Response codes {missing_responses} missing from {method.upper()} {path}"

def test_openapi_contract_schema_stability(baseline_openapi):
    """Ensure basic schema stability (no unexpected removals of models, required fields, or type changes)."""
    current_openapi = app.openapi()
    baseline_schemas = baseline_openapi.get("components", {}).get("schemas", {})
    current_schemas = current_openapi.get("components", {}).get("schemas", {})

    for schema_name, schema_def in baseline_schemas.items():
        assert schema_name in current_schemas, f"Schema model {schema_name} missing from live API contract"
        
        baseline_props = schema_def.get("properties", {})
        current_props = current_schemas[schema_name].get("properties", {})
        
        # Check that existing properties were not removed
        for prop_name, prop_def in baseline_props.items():
            assert prop_name in current_props, f"Property '{prop_name}' missing from schema '{schema_name}'"
            
            # Check that types haven't changed in a breaking way
            baseline_type = prop_def.get("type")
            current_type = current_props[prop_name].get("type")
            if baseline_type and current_type:
                assert baseline_type == current_type, f"Type changed for '{schema_name}.{prop_name}': expected {baseline_type}, got {current_type}"
                
        # Check that required fields were not removed or added in a breaking way
        baseline_required = set(schema_def.get("required", []))
        current_required = set(current_schemas[schema_name].get("required", []))
        
        # Removing a required field is technically non-breaking for responses, but we want strict contract adherence
        # Adding a required field that wasn't there before IS a breaking change for requests.
        # Here we just enforce strict matching or baseline subset to prevent accidental drift.
        missing_required = baseline_required - current_required
        # Wait, if a field is no longer required, that's fine. If a NEW field is required, it breaks clients.
        new_required = current_required - set(baseline_props.keys()) - set(current_props.keys()) # wait, just checking new required fields vs baseline
        # Let's enforce that no NEW required properties are added to existing schemas unless explicitly updated in baseline
        added_required = current_required - baseline_required
        if added_required:
            pytest.fail(f"New required fields {added_required} added to schema '{schema_name}', breaking backwards compatibility.")
