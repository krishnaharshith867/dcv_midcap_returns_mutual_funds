"""Regenerate render_app/dashboards/p*.py from the dashboard notebook.

Run from the project root:
    python build_app.py

Workflow:
    Edit Midcap_Mutual_Funds_Dashboard_Render.ipynb
    -> run this script
    -> test the Render entry point
    -> commit and push

Generated modules are derived from notebook cells. Do not edit them manually.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "Midcap_Mutual_Funds_Dashboard_Render.ipynb"
OUT = ROOT / "render_app" / "dashboards"

# (module name, notebook code-cell indices, description)
# These indices were checked against the uploaded 54-cell notebook.
PARTS = [
    ("p0_shared_setup", [2, 4, 6, 8, 9, 10],
     "Imports, data loading, shared palette/helpers and Dashboard 1"),
    ("p1_commission_cost", [12, 13],
     "Dashboard 2: the cost of investing"),
    ("p2_direct_vs_regular", [15, 16],
     "Dashboard 3: Direct versus Regular plans"),
    ("p3_cost_vs_return", [20, 22, 24, 26, 28, 30, 32],
     "Dashboard 4: expense ratio versus returns"),
    ("p4_risk_crashes", [36, 38, 40, 42, 44],
     "Dashboard 5: risk and market crashes"),
    ("p5_scorecard", [46, 47],
     "Dashboard 6: fund-house scorecard"),
    ("p6_extras_and_audit", [49, 50, 52],
     "Additional analytical plots and Dashboard 7: data quality audit"),
    ("p7_shell", [53],
     "Shared Dash navigation shell and callbacks"),
]

# Guard against notebook edits shifting cells without updating this script.
EXPECT_START = {
    2: "import numpy as np",
    4: "from pathlib import Path",
    6: 'ter = ter[ter["MF_ID"].isin(nav["MF_ID"].unique())].copy()',
    8: "# ---------- numbers for the overview ----------",
    9: "# ---------- helpers ----------",
    10: "title0, cards0, fig_nav0, fig_ter0, table0",
    12: "# ---------- Dashboard 2: what does the commission cost? ----------",
    15: "# ---------- Dashboard 3: do Direct plans really earn more? ----------",
    20: "# ---------- Dashboard 4: setup ----------",
    22: "# ---------- Dashboard 4: the numbers behind the charts ----------",
    24: "# ---------- chart 1: average TER vs return ----------",
    26: "# ---------- chart 2: four cost groups, average return ----------",
    28: "# ---------- chart 3: is it the same every year? ----------",
    30: "# ---------- chart 4: the face-off, growth of Rs 10,000 ----------",
    32: "# ---------- Dashboard 4: the app ----------",
    36: "# ---------- Dashboard 5: setup ----------",
    38: "# ---------- chart 1: risk vs return (bubble size = TER) ----------",
    40: "# ---------- chart 2: March 2020 crash test ----------",
    42: "# ---------- chart 3: rolling 1-year return bands ----------",
    44: "# ---------- Dashboard 5: the app ----------",
    46: "# ---------- Dashboard 6: calculations ----------",
    47: "# ---------- Dashboard 6: interactive Dash app ----------",
    49: "# ============================================================",
    50: "# ============================================================",
    52: "# ---------- Dashboard 7: before vs after cleaning ----------",
    53: "# ---------- Final: one app, seven dashboards, switched from the top bar ----------",
}


def cell_source(cell):
    """Notebook source can be stored as either a list of lines or one string."""
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


def transform_shared_setup(source):
    """Make data paths resolve from the repository root, not this module's folder."""
    old_base = (
        'BASE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()'
    )
    if old_base not in source:
        raise ValueError("Could not find the expected BASE assignment in notebook cell 4.")

    source = source.replace(
        old_base,
        'PROJECT_ROOT = Path(__file__).resolve().parents[2]\n'
        'DATA_DIR = PROJECT_ROOT / "data_collection" / "clean"',
        1,
    )
