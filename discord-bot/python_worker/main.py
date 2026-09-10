"""Bounded job polling loop for the process-separated modular monolith."""

from __future__ import annotations

import logging
import signal
import time

from dotenv import load_dotenv

from server.guildpilot.config import Settings
from server.guildpilot.supabase_gateway import SupabaseGateway

log = logging.getLogger("guildpilot.worker")
running = True


def stop(*_: object) -> None:
    global running
    running = False


def run() -> None:
    settings = Settings.from_env()
    gateway = SupabaseGateway(settings)
    if not gateway.configured:
        raise SystemExit("Supabase server credentials are required to start the worker")

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    log.info("Worker ready; no handlers are enabled until a job contract is registered")
    while running:
        time.sleep(5)


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run()

