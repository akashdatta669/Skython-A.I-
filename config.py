"""
config.py — Central configuration for Skython AI
All ports, paths, model names, and tunables live here.
"""

import os
import socket
import sys
import logging
from pathlib import Path

# ─────────────────────────── Paths ────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).parent
DB_PATH: Path = BASE_DIR / "skython.db"
LOG_PATH: Path = BASE_DIR / "skython.log"
DATA_DIR: Path = BASE_DIR / "data"
TOPICS_DIR: Path = DATA_DIR / "topics"
SKILLS_DIR: Path = DATA_DIR / "skills"
SANDBOX_TMP_DIR: Path = BASE_DIR / ".sandbox_tmp"

# ─────────────────────────── Ollama ───────────────────────────────────────────
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_PREFERRED_MODELS: list[str] = ["gemma3:1b", "gemma3:4b", "gemma3", "llama3.2:1b", "llama3.2", "mistral"]
OLLAMA_DEFAULT_MODEL: str = "gemma3:1b"
OLLAMA_MAX_TOKENS: int = 2048
OLLAMA_TIMEOUT: int = 120  # seconds
OLLAMA_RETRY_COUNT: int = 3
OLLAMA_RETRY_DELAY: float = 1.0  # seconds

# ─────────────────────────── Ports ────────────────────────────────────────────
GRADIO_PORT_START: int = 7860
BACKEND_PORT_START: int = 8000
MCP_PORT_START: int = 8001

# ─────────────────────────── Security ─────────────────────────────────────────
MAX_INPUT_LENGTH: int = 4096
SANDBOX_TIMEOUT: int = 10  # seconds
BLOCKED_MODULES: list[str] = [
    "os", "sys", "subprocess", "socket", "http", "urllib",
    "shutil", "ctypes", "importlib", "pathlib", "pickle",
    "marshal", "shelve", "pty", "tty", "termios", "signal",
    "multiprocessing", "threading", "concurrent", "asyncio",
    "ftplib", "smtplib", "telnetlib", "xmlrpc", "wsgiref",
    "antigravity", "this",
]
BLOCKED_BUILTINS: list[str] = [
    "eval", "exec", "compile", "__import__", "open",
    "breakpoint", "input", "memoryview",
]

# ─────────────────────────── Teaching ─────────────────────────────────────────
MAX_HINT_LEVELS: int = 3
MASTERY_THRESHOLDS: dict[str, tuple[float, float]] = {
    "novice":       (0.0, 0.2),
    "beginner":     (0.2, 0.4),
    "intermediate": (0.4, 0.6),
    "advanced":     (0.6, 0.8),
    "expert":       (0.8, 1.0),
}
MASTERY_PROMOTION_MIN_SCORE: float = 0.8
MASTERY_PROMOTION_MIN_EXERCISES: int = 3
MASTERY_SUCCESS_WEIGHT: float = 0.3   # EMA weight for success
MASTERY_FAILURE_WEIGHT: float = 0.3   # EMA weight for failure

# ─────────────────────────── Logging ──────────────────────────────────────────
LOG_FORMAT: str = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL: int = logging.DEBUG

# ─────────────────────────── Helpers ──────────────────────────────────────────

def find_free_port(start: int, exclude: list[int] | None = None) -> int:
    """Scan upward from `start` until a free TCP port is found."""
    exclude = exclude or []
    port = start
    while True:
        if port in exclude:
            port += 1
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1


def setup_logging() -> None:
    """Configure root logger → console + rotating file handler."""
    import io
    import logging.handlers

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Avoid duplicate handlers if called multiple times
    if root.handlers:
        return

    fmt = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler — use UTF-8 stream to handle emoji in log messages on Windows
    try:
        utf8_stream = io.TextIOWrapper(
            sys.stdout.buffer if hasattr(sys.stdout, "buffer") else sys.stdout,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
        ch = logging.StreamHandler(stream=utf8_stream)
    except Exception:
        ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # File handler (rotate at 5 MB, keep 3 backups)
    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(fmt)
    root.addHandler(fh)


def get_mastery_level(score: float) -> str:
    """Map a 0-1 score to a mastery level string."""
    for level, (lo, hi) in MASTERY_THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return "expert"


# Ensure runtime directories exist
SANDBOX_TMP_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
TOPICS_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
