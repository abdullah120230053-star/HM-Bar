import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

PROFILE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DynamicIslandPro"
PREFERENCES = PROFILE / "preferences.json"


def read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_preferences(changes):
    PROFILE.mkdir(parents=True, exist_ok=True)
    data = {**read_json(PREFERENCES), **changes}
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=PROFILE, delete=False) as file:
        temporary = Path(file.name)
        json.dump(data, file, indent=2)
    try:
        temporary.replace(PREFERENCES)
    finally:
        temporary.unlink(missing_ok=True)
