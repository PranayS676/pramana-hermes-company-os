from __future__ import annotations

import os

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8002


def main() -> None:
    host, port = server_config_from_env()
    uvicorn.run("hermes_company_os.main:app", host=host, port=port, reload=True)


def server_config_from_env() -> tuple[str, int]:
    host = os.getenv("HERMES_COMPANY_OS_HOST", DEFAULT_HOST)
    port = int(os.getenv("HERMES_COMPANY_OS_PORT", str(DEFAULT_PORT)))
    return host, port
