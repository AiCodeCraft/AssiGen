import json
from pathlib import Path

def load_config():
    config_path = Path(__file__).parent.parent / 'config.json'
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "default_model": "gpt-3.5-turbo",
            "max_file_size": 100000,
            "enable_logging": True
        }
