import os
from datetime import datetime, date

LOG_DIR = "logs"

def _ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

def get_log_path(callsign):
    _ensure_log_dir()
    sanitized = callsign.replace("/", "_").upper()
    return os.path.join(LOG_DIR, f"{sanitized}.log")

def append_log(callsign, sender_callsign, message):
    """
    callsign = the log file to write to (e.g. KC3UFO)
    sender_callsign = who actually said the message (e.g. KC3SMW or KC3UFO)
    """
    log_path = get_log_path(callsign)
    _ensure_log_dir()

    now = datetime.utcnow()
    today = now.strftime("%-m/%-d/%Y") if os.name != "nt" else now.strftime("%#m/%#d/%Y")
    timestamp = now.strftime("[%H:%M:%S]")

    insert_date_header = True
    if os.path.exists(log_path):
        with open(log_path, "rb") as f:
            try:
                recent_lines = f.readlines()[-20:]
                for line in reversed(recent_lines):
                    if line.decode(errors="ignore").strip().endswith(":") and today in line.decode():
                        insert_date_header = False
                        break
            except Exception:
                pass

    with open(log_path, "a", encoding="utf-8") as f:
        if insert_date_header:
            f.write(f"{today}:\n")
        f.write(f"{timestamp} {sender_callsign}: {message}\n")


def get_log(callsign):
    log_path = get_log_path(callsign)
    if not os.path.exists(log_path):
        return ""
    with open(log_path, "r", encoding="utf-8") as f:
        return f.read()

def clear_log(callsign):
    log_path = get_log_path(callsign)
    if os.path.exists(log_path):
        os.remove(log_path)
