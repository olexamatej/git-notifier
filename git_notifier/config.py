from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


DEFAULT_SOUND_NAME = "metal-pipe"
DEFAULT_SOUND_URL = "https://www.youtube.com/watch?v=iDLmYZ5HqgM"


@dataclass
class Config:
    sounds: dict[str, str] = field(
        default_factory=lambda: {DEFAULT_SOUND_NAME: DEFAULT_SOUND_URL}
    )
    default_sound: str = DEFAULT_SOUND_NAME
    player_command: list[str] | None = None
    play_seconds: float = 3.0
    poll_seconds: float = 10.0
    max_sounds_per_cycle: int = 8
    include_local: bool = True
    include_remote: bool = True
    fetch: bool = True


def default_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return base / "git-notifier" / "config.json"


def default_state_dir() -> Path:
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg_state_home) if xdg_state_home else Path.home() / ".local" / "state"
    return base / "git-notifier"


def default_state_path(repo_path: Path) -> Path:
    resolved = repo_path.expanduser().resolve()
    digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", resolved.name).strip("-") or "repo"
    return default_state_dir() / f"{slug}-{digest}.json"


def load_config(path: Path | None = None) -> Config:
    config_path = path or default_config_path()
    if not config_path.exists():
        config = Config()
        save_config(config, config_path)
        return config

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return _config_from_dict(data)


def save_config(config: Config, path: Path | None = None) -> None:
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(asdict(config), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _config_from_dict(data: dict[str, Any]) -> Config:
    defaults = Config()
    values = asdict(defaults)
    values.update({key: value for key, value in data.items() if key in values})

    sounds = values.get("sounds")
    if not isinstance(sounds, dict) or not sounds:
        sounds = defaults.sounds
    values["sounds"] = {str(name): str(url) for name, url in sounds.items()}

    default_sound = str(values.get("default_sound") or DEFAULT_SOUND_NAME)
    if default_sound not in values["sounds"]:
        values["sounds"][default_sound] = DEFAULT_SOUND_URL
    values["default_sound"] = default_sound

    player_command = values.get("player_command")
    if player_command is not None:
        values["player_command"] = [str(part) for part in player_command]

    values["play_seconds"] = float(values["play_seconds"])
    values["poll_seconds"] = float(values["poll_seconds"])
    values["max_sounds_per_cycle"] = int(values["max_sounds_per_cycle"])
    values["include_local"] = bool(values["include_local"])
    values["include_remote"] = bool(values["include_remote"])
    values["fetch"] = bool(values["fetch"])
    return Config(**values)


def load_state(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    refs = data.get("refs", {})
    if not isinstance(refs, dict):
        return {}
    return {str(ref): str(sha) for ref, sha in refs.items()}


def save_state(path: Path, refs: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"refs": dict(sorted(refs.items()))}
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
