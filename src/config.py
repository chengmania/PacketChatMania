# config.py
import configparser
import os

CONFIG_FILE = "config.ini"

default_config = {
    "TNC": {
        "host": "127.0.0.1",
        "port": "8001"
    },
    "User": {
        "callsign": "N0CALL",
        "cq_message": "CQ CQ CQ de N0CALL"
    },
    "Beacon": {
    "enabled": "false",
    "interval": "15",
    "message": "ChatMania App with mailbox",
    "digipeater": ""
    }
}

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
    config.read(CONFIG_FILE)
    return config

def save_config(config_dict):
    config = configparser.ConfigParser()
    for section, settings in config_dict.items():
        config[section] = settings
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
