# Script guidance

This directory contains equivalent Docker start and stop scripts for supported platforms:

- `start.ps1` and `stop.ps1` support Windows PowerShell.
- `start.sh` and `stop.sh` support macOS and Linux POSIX shells.

All scripts operate only on the `pm-mvp` container and use the `pm-mvp:local` image. Keep platform behavior and command-line settings aligned when changing a script. Scripts must remain safe to rerun and must resolve the repository root relative to their own location.
