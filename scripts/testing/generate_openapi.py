import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.main import app

def generate_openapi_schema(output_path: str):
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    print(f"OpenAPI schema successfully exported to {output_path}")

if __name__ == "__main__":
    out_path = Path(__file__).parent.parent.parent / "testing" / "contracts" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    generate_openapi_schema(str(out_path))
