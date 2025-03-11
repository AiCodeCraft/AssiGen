import json
import logging
from pathlib import Path

def load_config():
    config_path = Path(__file__).parent.parent / "config.json"
    default_config = {
        "environment": {
            "cache_dir": "/tmp/default_cache",
            "max_temp_files": 50,
            "cleanup_interval": 1800
        },
        # ... (alle anderen Standardwerte)
    }

    try:
        with open(config_path, "r") as f:
            user_config = json.load(f)
            return deep_merge(default_config, user_config)
    except Exception as e:
        logging.warning(f"Config error: {str(e)}, using defaults")
        return default_config

def deep_merge(base, update):
    """Rekursives Merging von Config-Dictionaries"""
    for key, value in update.items():
        if isinstance(value, dict) and key in base:
            base[key] = deep_merge(base.get(key, {}), value)
        else:
            base[key] = value
    return base
