from __future__ import annotations

from pathlib import Path
import time

from .audio import AudioPlayer
from .config import Config, default_state_path, load_state, save_state
from .git import GitError, GitRepo, RefEvent


def watch_repo(
    repo_path: Path,
    config: Config,
    *,
    sound_name: str | None = None,
    interval: float | None = None,
    state_path: Path | None = None,
    notify_initial: bool = False,
    once: bool = False,
    fetch: bool | None = None,
    include_local: bool | None = None,
    include_remote: bool | None = None,
) -> None:
    repo = GitRepo(repo_path)
    repo.validate()

    state_file = state_path or default_state_path(repo.path)
    player = AudioPlayer(config.player_command)
    chosen_sound = sound_name or config.default_sound
    sound_url = _sound_url(config, chosen_sound)
    sleep_for = interval if interval is not None else config.poll_seconds
    should_fetch = config.fetch if fetch is None else fetch
    local = config.include_local if include_local is None else include_local
    remote = config.include_remote if include_remote is None else include_remote

    print(f"Watching {repo.path}")
    print(f"State: {state_file}")
    print(f"Sound: {chosen_sound} -> {sound_url}")

    while True:
        if should_fetch:
            try:
                repo.fetch_all()
            except GitError as exc:
                print(f"Fetch failed: {exc}")

        state_exists = state_file.exists()
        previous = load_state(state_file)
        current_infos = repo.refs(include_local=local, include_remote=remote)
        current = {ref: info.sha for ref, info in current_infos.items()}
        events = repo.detect_events(
            previous,
            current_infos,
            notify_initial=notify_initial or state_exists,
        )

        if not state_exists and not notify_initial:
            print(f"Baseline captured for {len(current)} refs.")
        elif events:
            _print_events(events)
            _play_for_events(player, sound_url, config.play_seconds, config.max_sounds_per_cycle, events)

        save_state(state_file, current)
        notify_initial = False

        if once:
            return
        time.sleep(sleep_for)


def reset_repo_state(repo_path: Path, state_path: Path | None = None) -> Path:
    repo = GitRepo(repo_path)
    repo.validate()
    state_file = state_path or default_state_path(repo.path)
    if state_file.exists():
        state_file.unlink()
    return state_file


def play_sound(config: Config, name_or_url: str | None, seconds: float | None = None) -> None:
    name_or_url = name_or_url or config.default_sound
    url = config.sounds.get(name_or_url, name_or_url)
    player = AudioPlayer(config.player_command)
    result = player.play(url, seconds if seconds is not None else config.play_seconds)
    if not result.played:
        print(result.message)


def _sound_url(config: Config, sound_name: str) -> str:
    if "://" in sound_name:
        return sound_name
    try:
        return config.sounds[sound_name]
    except KeyError as exc:
        available = ", ".join(sorted(config.sounds)) or "none"
        raise SystemExit(f"Unknown sound '{sound_name}'. Available sounds: {available}") from exc


def _print_events(events: list[RefEvent]) -> None:
    for event in events:
        short_old = event.old_sha[:8] if event.old_sha else "new"
        short_new = event.new_sha[:8]
        print(f"{event.kind}: {event.ref} {short_old} -> {short_new}")
        for commit in event.commits:
            print(f"  {commit.sha[:8]} {commit.subject}")


def _play_for_events(
    player: AudioPlayer,
    sound_url: str,
    seconds: float,
    max_sounds: int,
    events: list[RefEvent],
) -> None:
    sounds_to_play = min(max_sounds, sum(event.sound_count for event in events))
    if sounds_to_play <= 0:
        return

    for index in range(sounds_to_play):
        result = player.play(sound_url, seconds)
        if not result.played:
            print(result.message)
            return
        if index == 0 and sounds_to_play > 1:
            print(f"Playing {sounds_to_play} notifications.")
