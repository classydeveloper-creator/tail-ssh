# Tail-SSH
A lightweight, zero-dependency Python CLI wrapper around `tailscale status --json` for listing peers, inspecting machine details, and launching SSH sessions in your terminal.

## Requirements
- **Python 3.10+** (uses only the Python standard library)
- **Tailscale** installed and available on `PATH` (`tailscale status --json`)
- A terminal emulator (defaults to `konsole`, or set `$TERMINAL`)

## Installation
Keep the script in its own project directory and expose it on `PATH` via a symlink:
```bash
mkdir -p ~/tail-ssh ~/.local/bin
chmod +x ~/tail-ssh/tailssh.py
ln -sf ~/tail-ssh/tailssh.py ~/.local/bin/tail-ssh
```

Optional environment variables:
```bash
# Override the terminal used to launch SSH windows (default: konsole)
export TERMINAL="konsole"
```

## Usage
### Interactive Mode
Launch `tail-ssh` with no arguments to enter the interactive prompt:
```bash
tail-ssh
```

Available commands at the `-> ` prompt:

| Command | Description | Example |
|---|---|---|
| `machines` | List tailnet peers, chosen IP, and online/offline state | `machines` or `machines ipv6` |
| `details <hostname>` | Show DNS name, OS, IPs, online state, and relay info | `details my-server` |
| `ssh` | Pick a peer interactively (or pass flags for one-shot launch) | `ssh index:1 name:ubuntu` |
| `refresh` | Re-run `tailscale status --json` and refresh cached peers | `refresh` |
| `help` | List available commands (also accepts `?`, `commands`, `cmd`, `how`, `explain`) | `help` |
| `exit` | Quit the CLI | `exit` |

### One-Shot CLI Mode

Pass a command directly as arguments to run once and exit:
```bash
tail-ssh machines
tail-ssh machines ipv6
tail-ssh details my-server
tail-ssh ssh index:1 name:debian
```

When prompted for `ssh-user`, pressing `Enter` falls back to `\$USER` / the current system username.![alt text](tailsshlogo.webp)