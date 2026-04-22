# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run during development:**
```sh
python localforward.py <command> [options]
```

**Build standalone binary** (output goes to `dist/localforward`):
```sh
pyinstaller localforward.spec
```

**Install dependencies in virtual environment:**
```sh
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

There are no tests in this project.

## Architecture

All application logic lives in a single file: `localforward.py` (~224 lines). It is a Python CLI tool that manages SSH tunnels for local development on macOS/Linux.

**Command dispatch** is handled in `main()` via `argparse` subparsers. Each subcommand maps directly to a function.

**State is file-based:**
- `~/.localforward_config.json` — persists the default SSH profile name across sessions
- `/tmp/localforward_tunnel.pid` — PID of the active SSH subprocess
- `/tmp/localforward.log` — stdout/stderr of the SSH process
- `/etc/hosts` — host-to-loopback-IP mappings tagged with `# Added by LocalForward`

**How `add <host>` works:** Scans `/etc/hosts` for existing tagged entries to find the next free loopback IP in `127.0.0.2–254`, appends the mapping to `/etc/hosts`, then calls `sudo ifconfig lo0 alias <ip>` to activate it on the loopback interface. After adding, it auto-restarts any active tunnel.

**How `start [profile]` works:** Reads `~/.ssh/config` via `paramiko.SSHConfig`, extracts `hostname`, `user`, and `identityfile` for the named profile, then builds an `ssh` command with `-L <loopback_ip>:80:<host>:80` for every tagged `/etc/hosts` entry, and spawns it as a background subprocess.

**`ensure_sudo()`** is called at the start of commands that need root (`add`, `start`, `stop`, `restart`, `logs`). It re-executes the current process under `sudo` if not already root.

**`restart`** reads the PID file, calls `stop_tunnel()`, then `start_ssh_tunnel()`. Note: `restart` is handled in `main()` but has no registered argparse subparser — it's reachable only if the string `"restart"` is passed as a command directly.

## Key constraints

- The `start_tunnel()` function destructures `ssh_config.values()` positionally as `hostname, user, identityfile` — the dict must contain exactly these three keys in this order, which depends on `get_ssh_profile_details()` returning the right paramiko lookup fields.
- Port forwarding is hardcoded to port 80 on both local and remote sides.
- Loopback IPs are limited to `127.0.0.2–254` (253 max hosts).
