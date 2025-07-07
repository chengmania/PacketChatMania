import os
import json
from datetime import datetime

HEARD_FILE = os.path.join("logs", "heard_stations.json")

def _ensure_logs_dir():
    if not os.path.exists("logs"):
        os.makedirs("logs")

def load_heard_stations():
    _ensure_logs_dir()
    if not os.path.exists(HEARD_FILE):
        return {}
    try:
        with open(HEARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_heard_stations(heard_dict):
    _ensure_logs_dir()
    with open(HEARD_FILE, "w", encoding="utf-8") as f:
        json.dump(heard_dict, f, indent=2)
