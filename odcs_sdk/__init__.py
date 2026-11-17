"""
ODCS (Open Digital Continuity Standard) Official Python SDK
Dual-Engine Language Toolchain & Runtime for Star Language and Haven Language.

Standard: ODCS-2.0.0
Architect: Anirudha Puthraya
Foundation: ODCS Standards Foundation
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "Anirudha Puthraya"
__standard__ = "ODCS-2.0.0"

from . import star
from . import haven
from . import natural
from .bridge import ContinuityBridge

# Convenient top-level shortcuts
run_star = star.run
eval_star = star.eval
is_star_valid = star.is_valid
run_haven = haven.run
transpile_haven = haven.compile
compile_star_wasm = star.compile_wasm
ZeroIntentLoss = haven.ZeroIntentLoss
ContinuityLedger = haven.ContinuityLedger
PNCounter = haven.PNCounter
DurableRecord = haven.DurableRecord

# Natural English to Star UI & Backend compiler
english_to_star_ui = natural.to_star_ui
english_to_star_backend = natural.to_star_backend
compile_english = natural.compile_english
run_english = natural.run_english

__all__ = [
    "__version__",
    "__author__",
    "__standard__",
    "star",
    "haven",
    "natural",
    "ContinuityBridge",
    "run_star",
    "eval_star",
    "is_star_valid",
    "run_haven",
    "transpile_haven",
    "compile_star_wasm",
    "ZeroIntentLoss",
    "ContinuityLedger",
    "PNCounter",
    "DurableRecord",
    "english_to_star_ui",
    "english_to_star_backend",
    "compile_english",
    "run_english",
]

