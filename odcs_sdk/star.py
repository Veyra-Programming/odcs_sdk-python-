"""
Star Programming Language Python Interface
Authoritative Reference: STAR_ROADMAP.md & STAR_SPEC.md

Enables authoring, compiling, running, and analyzing Star source code directly from Python.
Works standalone on PyPI and seamlessly binds to local Star SDK toolchains.
"""

from __future__ import annotations

import importlib
import os
import sys
import textwrap
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Module-level references for Star Engine components (Pyright/Pylance typing)
# ---------------------------------------------------------------------------
Lexer: Any = None
Parser: Any = None
SemanticAnalyzer: Any = None
StarCompiler: Any = None
StarVM: Any = None
WasmCompiler: Any = None

# ---------------------------------------------------------------------------
# Resilient Multi-Tier Engine Discovery (Self-Contained for PyPI)
# ---------------------------------------------------------------------------

STAR_AVAILABLE = False
STAR_SOURCE = "none"
STAR_SDK_DIR = os.environ.get("STAR_SDK", "")

# Tier 1: Try bundled engine (when packaged for PyPI inside odcs-sdk)
try:
    from .star_engine.lexer import Lexer as _BundledLexer
    from .star_engine.parser import Parser as _BundledParser
    from .star_engine.analyzer import SemanticAnalyzer as _BundledAnalyzer
    from .star_engine.compiler import StarCompiler as _BundledCompiler
    from .star_engine.vm import StarVM as _BundledVM
    from .star_backend.wasm.compiler import WasmCompiler as _BundledWasmCompiler

    Lexer = _BundledLexer
    Parser = _BundledParser
    SemanticAnalyzer = _BundledAnalyzer
    StarCompiler = _BundledCompiler
    StarVM = _BundledVM
    WasmCompiler = _BundledWasmCompiler
    STAR_AVAILABLE = True
    STAR_SOURCE = "bundled"
except (ImportError, Exception):
    pass

# Tier 2: Try top-level star_engine (if installed globally or in site-packages)
if not STAR_AVAILABLE:
    try:
        _lexer_mod = importlib.import_module("star_engine.lexer")
        _parser_mod = importlib.import_module("star_engine.parser")
        _analyzer_mod = importlib.import_module("star_engine.analyzer")
        _compiler_mod = importlib.import_module("star_engine.compiler")
        _vm_mod = importlib.import_module("star_engine.vm")
        _wasm_mod = importlib.import_module("star_backend.wasm.compiler")

        Lexer = getattr(_lexer_mod, "Lexer")
        Parser = getattr(_parser_mod, "Parser")
        SemanticAnalyzer = getattr(_analyzer_mod, "SemanticAnalyzer")
        StarCompiler = getattr(_compiler_mod, "StarCompiler")
        StarVM = getattr(_vm_mod, "StarVM")
        WasmCompiler = getattr(_wasm_mod, "WasmCompiler")
        STAR_AVAILABLE = True
        STAR_SOURCE = "global"
    except (ImportError, AttributeError, Exception):
        pass

# Tier 3: Auto-discover from standard installation paths
if not STAR_AVAILABLE:
    candidate_paths = [
        os.environ.get("STAR_SDK"),
        os.path.expandvars(r"%LOCALAPPDATA%\ODCS\star-sdk"),
        os.path.expandvars(r"%APPDATA%\Star Language"),
        r"C:\Program Files\Star Language",
        r"E:\Star Language",
        "/opt/odcs/star-sdk",
        "/usr/local/share/star",
        os.path.expanduser("~/.star"),
    ]
    for candidate in candidate_paths:
        if candidate and os.path.isdir(candidate):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            try:
                _lexer_mod = importlib.import_module("star_engine.lexer")
                _parser_mod = importlib.import_module("star_engine.parser")
                _analyzer_mod = importlib.import_module("star_engine.analyzer")
                _compiler_mod = importlib.import_module("star_engine.compiler")
                _vm_mod = importlib.import_module("star_engine.vm")
                _wasm_mod = importlib.import_module("star_backend.wasm.compiler")

                Lexer = getattr(_lexer_mod, "Lexer")
                Parser = getattr(_parser_mod, "Parser")
                SemanticAnalyzer = getattr(_analyzer_mod, "SemanticAnalyzer")
                StarCompiler = getattr(_compiler_mod, "StarCompiler")
                StarVM = getattr(_vm_mod, "StarVM")
                WasmCompiler = getattr(_wasm_mod, "WasmCompiler")
                STAR_AVAILABLE = True
                STAR_SOURCE = candidate
                STAR_SDK_DIR = candidate
                break
            except (ImportError, AttributeError, Exception):
                pass


class StarSDKError(RuntimeError):
    """Raised when Star toolchain operations fail."""


def _ensure_star():
    if not STAR_AVAILABLE:
        raise StarSDKError(
            "Star Engine could not be initialized. Please ensure the Star Language SDK "
            "is installed or set the 'STAR_SDK' environment variable."
        )


def _is_filepath(source_or_file: str) -> bool:
    """Safely check if an input is an existing file without raising OS path errors."""
    if not isinstance(source_or_file, str):
        return False
    if "\n" in source_or_file or "\r" in source_or_file or "\0" in source_or_file:
        return False
    if len(source_or_file) > 260:
        return False
    try:
        return os.path.isfile(source_or_file)
    except (ValueError, OSError):
        return False


def _preprocess(source_or_file: str) -> Tuple[str, str]:
    """Parse input as either a file path or raw Star source code."""
    if _is_filepath(source_or_file):
        with open(source_or_file, "r", encoding="utf-8") as f:
            code = f.read()
        filename = os.path.abspath(source_or_file)
    else:
        code = textwrap.dedent(str(source_or_file)).strip()
        filename = "<string>"
    return code, filename


def to_python(val: Any) -> Any:
    """
    Convert Star runtime values to native Python primitives.
    Converts StarInteger -> int, StarDecimal -> float, StarText -> str,
    StarBoolean -> bool, StarNull -> None, StarList -> list, StarMap -> dict.
    """
    if val is None:
        return None
    type_name = getattr(val, "type_name", "")
    if type_name == "Null":
        return None
    if hasattr(val, "value"):
        inner = val.value
        if isinstance(inner, (int, float, str, bool)):
            return inner
        if isinstance(inner, list):
            return [to_python(x) for x in inner]
        if isinstance(inner, dict):
            return {str(k): to_python(v) for k, v in inner.items()}
        return inner
    if hasattr(val, "elements"):
        return [to_python(x) for x in val.elements]
    if hasattr(val, "fields"):
        return {str(k): to_python(v) for k, v in val.fields.items()}
    return val


def check(source_or_file: str) -> bool:
    """Validate Star source code or file for syntax and semantic correctness."""
    _ensure_star()
    code, filename = _preprocess(source_or_file)

    lexer = Lexer(code, filename=filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source_code=code, filename=filename)
    prog = parser.parse()
    analyzer = SemanticAnalyzer(filename=filename, source_code=code)
    analyzer.analyze(prog)
    return True


def is_valid(source_or_file: str) -> bool:
    """Safely check if Star code is syntactically and semantically valid."""
    try:
        return check(source_or_file)
    except Exception:
        return False


def run(source: str, filename: str = "<string>", raw: bool = False) -> Any:
    """
    Execute Star source code inside the Star Virtual Machine.
    Returns native Python primitives by default, or raw StarValue if raw=True.
    """
    _ensure_star()
    code, fn = _preprocess(source)
    if filename != "<string>":
        fn = filename
    lexer = Lexer(code, filename=fn)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source_code=code, filename=fn)
    prog = parser.parse()
    compiler = StarCompiler(filename=fn, source_code=code)
    mod = compiler.compile(prog)
    vm = StarVM(mod)
    res = vm.run()
    if raw:
        return res
    return to_python(res)


def eval(expr: str) -> Any:
    """
    Evaluate a single Star expression and return native Python result.
    Example: star.eval("40 + 2") -> 42
    """
    return run(f"give back ({expr})\n")


def run_file(filepath: str) -> Any:
    """Execute a .star source file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Star file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    return run(code, filename=filepath)


def compile_wasm(source_or_file: str) -> bytes:
    """
    Compile Star source code directly into WebAssembly (WASM) binary bytecode.
    Returns raw bytes starting with magic header `\\0asm`.
    """
    _ensure_star()
    code, filename = _preprocess(source_or_file)

    lexer = Lexer(code, filename=filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source_code=code, filename=filename)
    prog = parser.parse()
    compiler = StarCompiler(filename=filename, source_code=code)
    mod = compiler.compile(prog)
    wasm_compiler = WasmCompiler(mod)
    return wasm_compiler.compile()


def compile_bytecode(source_or_file: str) -> bytes:
    """Compile Star source code into portable Star bytecode (.starb)."""
    _ensure_star()
    code, filename = _preprocess(source_or_file)

    lexer = Lexer(code, filename=filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source_code=code, filename=filename)
    prog = parser.parse()
    compiler = StarCompiler(filename=filename, source_code=code)
    mod = compiler.compile(prog)
    if hasattr(mod, "serialize"):
        return mod.serialize()
    import pickle
    return pickle.dumps(mod)


def tokens(source_or_file: str) -> List[Any]:
    """Tokenize Star source code and return token objects."""
    _ensure_star()
    code, filename = _preprocess(source_or_file)
    lexer = Lexer(code, filename=filename)
    return lexer.tokenize()


def ast(source_or_file: str) -> Any:
    """Parse Star source code and return AST representation."""
    _ensure_star()
    code, filename = _preprocess(source_or_file)
    lexer = Lexer(code, filename=filename)
    t = lexer.tokenize()
    parser = Parser(t, source_code=code, filename=filename)
    return parser.parse()
