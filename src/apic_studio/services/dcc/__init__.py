from __future__ import annotations

from collections.abc import Iterator

from .base import DCC, BaseBridge, CmdBuilder, RenderThread
from .c4d import Cinema4D, Cinema4DBridge, render_material, repath_textures
from .nuke import NukeBridge


class DCCBridge:
    """Every host app apic studio talks to, one bridge per app."""

    def __init__(self, c4d: Cinema4DBridge, nuke: NukeBridge) -> None:
        self.c4d = c4d
        self.nuke = nuke

    @classmethod
    def create(cls, timeout: float | None = 5) -> DCCBridge:
        return cls(Cinema4DBridge.create(timeout), NukeBridge.create(timeout))

    @property
    def bridges(self) -> tuple[BaseBridge, ...]:
        return (self.c4d, self.nuke)

    def __iter__(self) -> Iterator[BaseBridge]:
        return iter(self.bridges)


__all__ = [
    "DCC",
    "BaseBridge",
    "Cinema4D",
    "Cinema4DBridge",
    "CmdBuilder",
    "DCCBridge",
    "NukeBridge",
    "RenderThread",
    "render_material",
    "repath_textures",
]
