from __future__ import annotations

import argparse
from pathlib import Path

from .app import play_sound, reset_repo_state, watch_repo
from .config import load_config, save_config


def _add_config_arg(parser: argparse.ArgumentParser, default: object | None = None) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=default,
        help="Path to config JSON.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="git-notifier")
    _add_config_arg(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    watch = subparsers.add_parser("watch", help="Watch a repository for branch commits.")
    _add_config_arg(watch, default=argparse.SUPPRESS)
    watch.add_argument("repo", nargs="?", default=".", type=Path)
    watch.add_argument("--interval", type=float, help="Seconds between polls.")
    watch.add_argument("--state", type=Path, help="Path to watcher state JSON.")
    watch.add_argument("--sound", help="Configured sound name or direct URL to play.")
    watch.add_argument("--notify-initial", action="store_true", help="Play for refs seen on first run.")
    watch.add_argument("--once", action="store_true", help="Run one polling cycle and exit.")
    watch.add_argument("--fetch", dest="fetch", action="store_true", default=None)
    watch.add_argument("--no-fetch", dest="fetch", action="store_false")
    watch.add_argument("--local", dest="include_local", action="store_true", default=None)
    watch.add_argument("--no-local", dest="include_local", action="store_false")
    watch.add_argument("--remote", dest="include_remote", action="store_true", default=None)
    watch.add_argument("--no-remote", dest="include_remote", action="store_false")

    set_sound = subparsers.add_parser("set-sound", help="Add or replace a named sound URL.")
    _add_config_arg(set_sound, default=argparse.SUPPRESS)
    set_sound.add_argument("name")
    set_sound.add_argument("url")
    set_sound.add_argument("--default", action="store_true", help="Make this the default sound.")

    sounds = subparsers.add_parser("sounds", help="List configured sounds.")
    _add_config_arg(sounds, default=argparse.SUPPRESS)

    play = subparsers.add_parser("play", help="Play a configured sound name or direct URL.")
    _add_config_arg(play, default=argparse.SUPPRESS)
    play.add_argument("name_or_url", nargs="?")
    play.add_argument("--seconds", type=float)

    reset = subparsers.add_parser("reset", help="Reset saved baseline for a repository.")
    _add_config_arg(reset, default=argparse.SUPPRESS)
    reset.add_argument("repo", nargs="?", default=".", type=Path)
    reset.add_argument("--state", type=Path, help="Path to watcher state JSON.")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "watch":
        watch_repo(
            args.repo,
            config,
            sound_name=args.sound,
            interval=args.interval,
            state_path=args.state,
            notify_initial=args.notify_initial,
            once=args.once,
            fetch=args.fetch,
            include_local=args.include_local,
            include_remote=args.include_remote,
        )
    elif args.command == "set-sound":
        config.sounds[args.name] = args.url
        if args.default:
            config.default_sound = args.name
        save_config(config, args.config)
        default_note = " default" if config.default_sound == args.name else ""
        print(f"Saved{default_note} sound '{args.name}'.")
    elif args.command == "sounds":
        for name, url in sorted(config.sounds.items()):
            marker = " *" if name == config.default_sound else ""
            print(f"{name}{marker}: {url}")
    elif args.command == "play":
        play_sound(config, args.name_or_url, args.seconds)
    elif args.command == "reset":
        state_file = reset_repo_state(args.repo, args.state)
        print(f"Reset state: {state_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
