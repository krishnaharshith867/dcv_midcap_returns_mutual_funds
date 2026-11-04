
"""Main Render application entry point.

Executes generated dashboard modules in notebook order,
preserving their shared variables, callbacks and Dash app.
"""

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

DATA_DIR = PROJECT_ROOT / "data_collection" / "clean"

DASHBOARD_DIR = APP_DIR / "dashboards"

MODULES = [
    "p0_shared_setup.py",
    "p1_commission_cost.py",
    "p2_direct_vs_regular.py",
    "p3_cost_vs_return.py",
    "p4_risk_crashes.py",
    "p5_scorecard.py",
    "p6_extras_and_audit.py",
    "p7_shell.py",
]

# Execute all generated modules in one shared namespace.
# This preserves variables and callbacks defined in earlier modules.
namespace = globals()

for module_name in MODULES:
    module_path = DASHBOARD_DIR / module_name

    if not module_path.is_file():
        raise FileNotFoundError(
            f"Missing generated dashboard module: {module_path}. "
            "Run python build_app.py first."
        )

    print(f"Loading {module_name}...")

    namespace["__file__"] = str(module_path)

    exec(
        compile(
            module_path.read_text(encoding="utf-8"),
            str(module_path),
            "exec"
        ),
        namespace
    )

# Expose Flask server for Gunicorn.
server = app.server

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=False
    )
