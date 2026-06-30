"""Channel connector interface — normalize any channel into a common message.

Adding a channel = implementing this protocol; the engine and pipeline never change.
"""
from __future__ import annotations

from typing import Protocol

from ..tools.schemas import NormalizedMessage


class Connector(Protocol):
    channel: str
    def normalize(self, raw: dict) -> NormalizedMessage: ...
