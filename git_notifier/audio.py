from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Sequence


@dataclass(frozen=True)
class PlaybackResult:
    played: bool
    message: str


class AudioPlayer:
    def __init__(self, command_template: Sequence[str] | None = None):
        self.command_template = list(command_template) if command_template else None

    def play(self, url: str, seconds: float) -> PlaybackResult:
        command = self._command(url, seconds)
        if command is None:
            return PlaybackResult(
                played=False,
                message=(
                    "No supported player found. Install mpv plus yt-dlp, or set "
                    "player_command in ~/.config/git-notifier/config.json."
                ),
            )

        try:
            subprocess.run(command, check=False)
        except OSError as exc:
            return PlaybackResult(False, f"Could not run player: {exc}")
        return PlaybackResult(True, "played")

    def _command(self, url: str, seconds: float) -> list[str] | None:
        seconds_text = _format_seconds(seconds)
        if self.command_template:
            return [
                part.format(url=url, seconds=seconds_text)
                for part in self.command_template
            ]

        if shutil.which("mpv"):
            return [
                "mpv",
                "--no-video",
                "--really-quiet",
                "--force-window=no",
                f"--length={seconds_text}",
                url,
            ]

        if shutil.which("cvlc"):
            return [
                "cvlc",
                "--play-and-exit",
                "--no-video",
                f"--run-time={seconds_text}",
                url,
            ]

        return None


def _format_seconds(seconds: float) -> str:
    value = float(seconds)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")
