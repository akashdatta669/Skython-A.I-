"""
engines/sandbox.py — Secure Python code execution environment
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from config import SANDBOX_TIMEOUT, SANDBOX_TMP_DIR
from security.validator import validate_code

log = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time: float = 0.0
    error_type: str = ""   # "SecurityViolation" | "Timeout" | "RuntimeError" | "SyntaxError"
    error_message: str = ""


def execute_code(code: str, timeout: int = SANDBOX_TIMEOUT) -> ExecutionResult:
    """
    Execute Python code in a secure sandbox:
    1. AST security scan via validator.py
    2. Write to temp file in sandboxed directory
    3. Run via subprocess.Popen with clean environment
    4. Capture stdout/stderr, enforce timeout
    """
    import subprocess

    # ── Step 1: Security validation ─────────────────────────────────────────
    is_safe, violations = validate_code(code)
    if not is_safe:
        log.warning("Code execution blocked: %s", violations)
        return ExecutionResult(
            success=False,
            error_type="SecurityViolation",
            error_message="; ".join(violations),
            stderr="; ".join(violations),
        )

    # ── Step 2: Write to temp file ───────────────────────────────────────────
    run_id = uuid.uuid4().hex[:8]
    tmp_file = SANDBOX_TMP_DIR / f"run_{run_id}.py"

    try:
        tmp_file.write_text(code, encoding="utf-8")
    except OSError as exc:
        return ExecutionResult(
            success=False,
            error_type="RuntimeError",
            error_message=f"Failed to write temp file: {exc}",
        )

    # ── Step 3: Execute ──────────────────────────────────────────────────────
    # Clean environment — only PATH is passed
    clean_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": "",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    # On Windows, also need SystemRoot for the runtime to work
    if sys.platform == "win32":
        for key in ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP"):
            if key in os.environ:
                clean_env[key] = os.environ[key]

    start = time.perf_counter()
    try:
        proc = subprocess.Popen(
            [sys.executable, str(tmp_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(SANDBOX_TMP_DIR),
            shell=False,
            env=clean_env,
        )
        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return ExecutionResult(
                success=False,
                error_type="Timeout",
                error_message=f"Code execution exceeded {timeout}s time limit.",
                execution_time=time.perf_counter() - start,
            )

    except Exception as exc:
        return ExecutionResult(
            success=False,
            error_type="RuntimeError",
            error_message=str(exc),
            execution_time=time.perf_counter() - start,
        )
    finally:
        # Clean up temp file
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass

    elapsed = time.perf_counter() - start
    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    # ── Step 4: Classify result ──────────────────────────────────────────────
    error_type = ""
    error_message = ""

    if proc.returncode != 0 and stderr:
        if "SyntaxError" in stderr:
            error_type = "SyntaxError"
        elif "NameError" in stderr or "TypeError" in stderr or "ValueError" in stderr:
            error_type = "RuntimeError"
        else:
            error_type = "RuntimeError"
        error_message = stderr

    log.debug(
        "Sandbox execution: rc=%d time=%.3fs stdout=%d stderr=%d chars",
        proc.returncode,
        elapsed,
        len(stdout),
        len(stderr),
    )

    return ExecutionResult(
        success=proc.returncode == 0,
        stdout=stdout,
        stderr=stderr,
        return_code=proc.returncode,
        execution_time=elapsed,
        error_type=error_type,
        error_message=error_message,
    )
