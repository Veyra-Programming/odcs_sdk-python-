"""
Haven (Heaven) Language v2.0 Python Interface
Companion Natural-English & Advanced Continuity Runtime for ODCS-2.0.0.

Provides Pythonic bindings for:
  - Natural-English Haven transpilation and execution.
  - Zero Intent Loss (ZIL) cryptographic receipt minting.
  - Append-only Merkle DAG continuity ledgers.
  - Conflict-Free Replicated Data Types (CRDT PN-Counter).
  - RFC 8785 Canonical JSON & SHA-256 seal hashing.
"""

from __future__ import annotations

import ast
import builtins
import dataclasses
import hashlib
import importlib
import json
import os
import sys
import textwrap
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

# ---------------------------------------------------------------------------
# Module-level references for Haven Runtime components (Pyright typing)
# ---------------------------------------------------------------------------
_transpile_haven: Any = None
_HAVEN_PRELUDE: str = ""
HavenSyntaxError: Any = Exception

# Locate haven_lang module (first try bundled in package, then local paths)
HAVEN_AVAILABLE = False
try:
    from .haven_lang import (
        transpile_haven as _transpile_haven,
        HAVEN_PRELUDE as _HAVEN_PRELUDE,
        HavenSyntaxError,
    )
    HAVEN_AVAILABLE = True
except (ImportError, Exception):
    _haven_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "heaven")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        r"C:\Users\Admin\.gemini\config\plugins\heaven-language\skills\heaven-lang\scripts",
    ]
    for p in _haven_paths:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)

    try:
        _haven_mod = importlib.import_module("haven_lang")
        _transpile_haven = getattr(_haven_mod, "transpile_haven")
        _HAVEN_PRELUDE = getattr(_haven_mod, "HAVEN_PRELUDE", "")
        HavenSyntaxError = getattr(_haven_mod, "HavenSyntaxError", Exception)
        HAVEN_AVAILABLE = True
    except (ImportError, AttributeError, Exception):
        HAVEN_AVAILABLE = False


# ---------------------------------------------------------------------------
# Native Python ODCS Continuity Primitives
# ---------------------------------------------------------------------------

def canonical_json(obj: Any) -> str:
    """Deterministic RFC 8785 Canonical JSON serialization."""
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    elif dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        obj = dataclasses.asdict(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def seal_hash(value: Any) -> str:
    """Compute SHA-256 cryptographic seal of a canonical value."""
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = canonical_json(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def uuid7() -> str:
    """Generate monotonic UUIDv7 string with 48-bit millisecond timestamp."""
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_bytes = bytearray(uuid.uuid4().bytes)
    rand_bytes[0:6] = ts_ms.to_bytes(6, "big")
    rand_bytes[6] = (rand_bytes[6] & 0x0F) | 0x70
    rand_bytes[8] = (rand_bytes[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(rand_bytes)))


def now_ms() -> int:
    """Return current wall-clock time in epoch milliseconds."""
    return int(time.time() * 1000)


class ContinuityImmutabilityError(Exception):
    """Raised when attempting to mutate an ODCS sealed record."""


class PNCounter:
    """ODCS Layer 2 Conflict-Free Replicated Counter (PN-Counter)."""

    def __init__(self, node_id: str):
        self.node_id = str(node_id)
        self.p_map: Dict[str, int] = {self.node_id: 0}
        self.n_map: Dict[str, int] = {self.node_id: 0}

    def inc(self, step: int = 1) -> int:
        self.p_map[self.node_id] = self.p_map.get(self.node_id, 0) + int(step)
        return self.value()

    def dec(self, step: int = 1) -> int:
        self.n_map[self.node_id] = self.n_map.get(self.node_id, 0) + int(step)
        return self.value()

    def value(self) -> int:
        return sum(self.p_map.values()) - sum(self.n_map.values())

    def merge(self, other: "PNCounter") -> None:
        for k, v in other.p_map.items():
            self.p_map[k] = max(self.p_map.get(k, 0), v)
        for k, v in other.n_map.items():
            self.n_map[k] = max(self.n_map.get(k, 0), v)

    def state_hash(self) -> str:
        return seal_hash({"p": self.p_map, "n": self.n_map})


class ZeroIntentLoss:
    """ODCS Layer 4 Sub-16ms Local Authority Cryptographic Receipt Issuer."""

    @staticmethod
    def preserve(action: str, payload: Dict[str, Any], actor: str = "python-sdk") -> Dict[str, Any]:
        t0 = time.perf_counter()
        intent_id = f"zil_{uuid7()}"
        timestamp = now_ms()
        doc = {
            "intent_id": intent_id,
            "action": str(action),
            "payload": payload,
            "actor": str(actor),
            "timestamp_ms": timestamp,
            "standard": "ODCS-2.0.0",
        }
        receipt_hash = seal_hash(doc)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        doc["receipt_hash"] = receipt_hash
        doc["mint_duration_ms"] = round(duration_ms, 3)
        return doc


class ContinuityLedger:
    """ODCS Append-Only Write-Ahead-Log (WAL) and Merkle DAG Engine."""

    def __init__(self, uri: str = ":memory:"):
        self.uri = uri
        self.entries: List[Dict[str, Any]] = []

    @classmethod
    def open(cls, uri: str = ":memory:") -> "ContinuityLedger":
        return cls(uri)

    def append(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        height = len(self.entries) + 1
        prev_hash = self.entries[-1]["hash"] if self.entries else seal_hash("GENESIS_BLOCK")
        block = {
            "height": height,
            "prev_hash": prev_hash,
            "payload": entry,
            "timestamp_ms": now_ms(),
        }
        block["hash"] = seal_hash(block)
        self.entries.append(block)
        return block

    def merkle_root(self) -> str:
        if not self.entries:
            return seal_hash("EMPTY_LEDGER")
        level = [b["hash"] for b in self.entries]
        while len(level) > 1:
            if len(level) % 2 == 1:
                level.append(level[-1])
            nxt = []
            for i in range(0, len(level), 2):
                nxt.append(hashlib.sha256((level[i] + level[i + 1]).encode("utf-8")).hexdigest())
            level = nxt
        return level[0]


def DurableRecord(name: str, **fields_schema: Type[Any]) -> Any:
    """
    Factory for creating ODCS Durable Records in Python.
    Records are immutable, tamper-evident, and sealed with SHA-256.
    """
    class _Record:
        __odcs_name__ = name

        def __init__(self, **kwargs):
            for k, val in kwargs.items():
                object.__setattr__(self, k, val)
            object.__setattr__(self, "_sealed_hash", seal_hash(kwargs))

        def __setattr__(self, name, value):
            raise ContinuityImmutabilityError(f"Cannot mutate sealed record '{self.__odcs_name__}.{name}'")

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

        def seal(self) -> str:
            return getattr(self, "_sealed_hash", seal_hash(self.to_dict()))

        def __repr__(self):
            props = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
            return f"{name}({props})"

    _Record.__name__ = name
    return _Record


# ---------------------------------------------------------------------------
# Haven Language Source Code Transpiler & Runner
# ---------------------------------------------------------------------------

def compile(source_or_file: str, include_prelude: bool = True) -> str:
    """Transpile Haven Natural-English syntax into executable Python 3 code."""
    if not HAVEN_AVAILABLE:
        raise RuntimeError("Haven transpiler not available.")
    if os.path.exists(source_or_file):
        with open(source_or_file, "r", encoding="utf-8") as f:
            code = f.read()
    else:
        code = textwrap.dedent(source_or_file).strip()
    return _transpile_haven(code, include_prelude=include_prelude)


def lint(source_or_file: str) -> bool:
    """Validate Haven syntax without executing."""
    py_code = compile(source_or_file, include_prelude=True)
    ast.parse(py_code)
    return True


def run(source_or_file: str, context: Optional[Dict[str, Any]] = None, filename: str = "<haven-string>") -> Any:
    """
    Execute Haven Natural-English code in Python.
    If the snippet returns a value (via 'give back'), that value is returned.
    Otherwise, returns the execution namespace dictionary.
    """
    if os.path.exists(source_or_file):
        with open(source_or_file, "r", encoding="utf-8") as f:
            code = f.read()
        filename = source_or_file
    else:
        code = textwrap.dedent(str(source_or_file)).strip()

    ns: Dict[str, Any] = {
        "__name__": "__haven__",
        "__file__": filename,
        "PNCounter": PNCounter,
        "ZeroIntentLoss": ZeroIntentLoss,
        "ContinuityLedger": ContinuityLedger,
        "canonical_json": canonical_json,
        "seal_hash": seal_hash,
        "uuid7": uuid7,
        "now_ms": now_ms,
    }
    if context:
        ns.update(context)

    # Check if there is a top-level 'give back' or 'return'
    compiled_py = compile(code, include_prelude=True)
    try:
        exec(compile_code(compiled_py, filename, "exec"), ns)
        return ns
    except SyntaxError as e:
        if "'return' outside function" in str(e):
            wrapped_hvn = "define __haven_entry__():\n" + textwrap.indent(code, "    ") + "\nset __haven_result__ to __haven_entry__()\n"
            wrapped_py = compile(wrapped_hvn, include_prelude=True)
            exec(compile_code(wrapped_py, filename, "exec"), ns)
            return ns.get("__haven_result__")
        raise


def compile_code(source: str, filename: str, mode: str):
    """Helper to compile Python code string to code object."""
    return builtins.compile(source, filename, mode)
