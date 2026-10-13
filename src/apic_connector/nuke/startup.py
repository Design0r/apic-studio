from __future__ import absolute_import

import os

import nuke

from .compat import Logger, MessageRouter, Server
from .core import router as core_router

# must match the nuke socket port in the apic studio settings
DEFAULT_PORT = 1338

_server = None


def get_port():
    try:
        return int(os.environ.get("APIC_NUKE_PORT", DEFAULT_PORT))
    except ValueError:
        Logger.error("invalid APIC_NUKE_PORT, using {}".format(DEFAULT_PORT))
        return DEFAULT_PORT


def is_headless():
    return not nuke.GUI


def start():
    """Starts the apic studio connector, call it from the pipeline's init.py."""
    global _server

    if _server is not None:
        return

    if is_headless():
        return

    Logger.info("starting apic studio nuke connector... ")

    router = MessageRouter().include_router(core_router)

    # handlers touch the nuke api, which is only safe on the main thread
    _server = Server(port=get_port(), router=router, dispatch=nuke.executeInMainThread)
    _server.start()
