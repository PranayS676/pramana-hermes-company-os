from __future__ import annotations

import os
from pathlib import Path


def default_hermes_home() -> Path:
    configured = os.getenv("HERMES_HOME")
    if configured:
        return Path(configured).expanduser()

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "hermes"

    return Path.home() / ".hermes"


def default_profile_root() -> Path:
    return default_hermes_home() / "profiles"


def powershell_hermes_home_param() -> str:
    return (
        '$(if ($env:HERMES_HOME) { $env:HERMES_HOME } '
        'elseif ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "hermes" } '
        'else { Join-Path $env:USERPROFILE ".hermes" })'
    )


def powershell_profile_root_label() -> str:
    return "$HermesHome\\profiles"
