# Git Notifier

Hackathon commit siren. `git-notifier` watches every local and remote branch in a clone and plays a configurable sound when a branch receives new commits.

The default sound is the metal pipe clip:

```text
https://www.youtube.com/watch?v=iDLmYZ5HqgM
```

## Requirements

- Python 3.10+
- Git
- A player that can play YouTube URLs. `mpv` with `yt-dlp` available on the system is the recommended setup.

On Debian/Ubuntu-like systems:

```sh
sudo apt install mpv yt-dlp
```

## Install

From this repository:

```sh
python3 -m pip install -e .
```

You can also run it without installing:

```sh
python3 -m git_notifier watch /path/to/repo
```

## Watch A Repo

```sh
git-notifier watch /path/to/repo
```

By default, the first run records the current state and does not play sounds for old commits. After that, every poll fetches remotes, checks all local and remote branch refs, and plays the configured sound for new commits.

Useful options:

```sh
git-notifier watch . --interval 5
git-notifier watch . --once
git-notifier watch . --notify-initial
git-notifier watch . --no-fetch
git-notifier watch . --sound metal-pipe
git-notifier watch . --sound "https://www.youtube.com/watch?v=iDLmYZ5HqgM"
```

## Change Sounds

Add or replace a named sound with any URL your player can handle:

```sh
git-notifier set-sound airhorn "https://www.youtube.com/watch?v=example" --default
```

Test it:

```sh
git-notifier play airhorn
```

List configured sounds:

```sh
git-notifier sounds
```

Config lives at:

```text
~/.config/git-notifier/config.json
```

Per-repository watcher state lives under:

```text
~/.local/state/git-notifier/
```

## Player Override

If `mpv` is not the right integration on your machine, set a command template in the config. `{url}` and `{seconds}` are replaced at runtime.

Example:

```json
{
  "player_command": ["mpv", "--no-video", "--length={seconds}", "{url}"]
}
```

## Reset A Repo Baseline

```sh
git-notifier reset /path/to/repo
```
# git-notifier
