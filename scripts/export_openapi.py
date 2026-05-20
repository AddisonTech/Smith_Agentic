"""
scripts/export_openapi.py

Dumps the SmithAgentic FastAPI OpenAPI schema to openapi.json.
Run from the repo root:

    python scripts/export_openapi.py

Commit the output so the UI and MCP server can reference it without
needing to start the server.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.server import app

schema = app.openapi()
out = Path(__file__).resolve().parent.parent / "openapi.json"
out.write_text(json.dumps(schema, indent=2))
print(f"Schema written to {out}")