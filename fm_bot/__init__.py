"""Dofus Forgemage (FM / smithmagic) helper.

Client-side decision engine and optional mouse clicking for the user's own
Dofus window. See README.md for Ankama ToS warnings.
"""

from .engine import (
    ForgeSession,
    ItemFamily,
    ItemState,
    MageMode,
    Outcome,
    Recommendation,
    SessionLimits,
    StatLine,
)
from .runes import RUNE_BY_ID, STAT_BY_ID, get_rune, get_stat

__version__ = "1.0.0"

__all__ = [
    "ForgeSession",
    "ItemFamily",
    "ItemState",
    "MageMode",
    "Outcome",
    "Recommendation",
    "SessionLimits",
    "StatLine",
    "RUNE_BY_ID",
    "STAT_BY_ID",
    "get_rune",
    "get_stat",
    "__version__",
]
