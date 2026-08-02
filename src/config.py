"""Loads config.json once at import time. Every module reads tunables from CONFIG."""

import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(REPO_ROOT, "config.json")

with open(_CONFIG_PATH) as _f:
    CONFIG = json.load(_f)
