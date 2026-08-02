#!/usr/bin/env python3
"""Create launchd plists atomically without shell-interpolated XML."""

from __future__ import annotations

import argparse
import os
import plistlib
import tempfile
from pathlib import Path


def atomic_plist(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            plistlib.dump(data, handle, fmt=plistlib.FMT_XML, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--start-interval", type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    environment: dict[str, str] = {}
    for item in args.env:
        if "=" not in item:
            parser.error(f"invalid --env {item!r}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        environment[key] = value

    data: dict = {
        "Label": args.label,
        "ProgramArguments": command,
        "WorkingDirectory": args.cwd,
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ProcessType": "Interactive",
        "StandardOutPath": args.stdout,
        "StandardErrorPath": args.stderr,
    }
    if environment:
        data["EnvironmentVariables"] = environment
    if args.start_interval:
        data["ThrottleInterval"] = args.start_interval
    atomic_plist(args.output, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
