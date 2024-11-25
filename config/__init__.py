import yaml
from pathlib import Path

def load_settings():
    settings_path = Path(__file__).parent / "settings.yaml"
    with open(settings_path, "r") as f:
        return yaml.safe_load(f)

settings = load_settings()