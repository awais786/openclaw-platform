"""OpenClaw — standalone AI customer-engagement engine.

The engine knows only *tools*; where they run is a pluggable ToolBackend
(LocalBackend for standalone use, DjangoBackend to connect the Django app).
"""

from .config import Settings
from .engine import Engine

__version__ = "0.1.0"
__all__ = ["Engine", "Settings", "__version__"]
