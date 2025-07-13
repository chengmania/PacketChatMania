# tnclog.py
import os
from datetime import datetime
# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Define log file path with timestamp
TNC_LOG_FILE = os.path.join(LOG_DIR, f"tnc_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
def log_raw_line(line):
    timestamp = datetime.utcnow().strftime("[%Y-%m-%d %H:%M:%S UTC]")
    try:
        with open(TNC_LOG_FILE , "a") as f:
            f.write(f"{timestamp} {line}\n")
            f.flush()
    except Exception as e:
        print(f"⚠️ Failed to write TNC log: {e}")
