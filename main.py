from __future__ import annotations

import os

# Force third-party libraries to run in pure offline/silent mode
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

"""
main.py — Skython AI application entry point
Startup sequence: banner → port scan → DB init → Ollama check → engine init → servers → UI
"""

import logging
import sys
import threading
import time
from typing import Any

# ── Force UTF-8 stdout/stderr on Windows to avoid cp1252 UnicodeEncodeError ───
import io
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─────────────────────────── Version check (before any imports) ────────────────
if sys.version_info < (3, 10):
    print(f"Python 3.10+ required. You have {sys.version}. Aborting.")
    sys.exit(1)

# ─────────────────────────── Setup logging first ──────────────────────────────
import config as cfg

cfg.setup_logging()
log = logging.getLogger("skython.main")


# ─────────────────────────── Banner ───────────────────────────────────────────

def print_banner() -> None:
    banner = (
        "\n"
        "  +=========================================================+\n"
        "  |                                                         |\n"
        "  |   SSSSS  K   K  Y   Y  TTTTT  H   H  OOO   N   N      |\n"
        "  |   S      K  K    Y Y     T    H   H O   O  NN  N      |\n"
        "  |   SSSSS  KKK      Y      T    HHHHH O   O  N N N      |\n"
        "  |       S  K  K     Y      T    H   H O   O  N  NN      |\n"
        "  |   SSSSS  K   K    Y      T    H   H  OOO   N   N      |\n"
        "  |                                                         |\n"
        "  |              AI -- Offline Python Mentor                |\n"
        "  +=========================================================+\n"
    )
    # Force UTF-8 stdout on Windows to avoid cp1252 codec errors
    try:
        import io
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(banner)


# ─────────────────────────── Port scanning ────────────────────────────────────

def find_ports() -> tuple[int, int, int]:
    """Find free ports for backend, MCP, and Gradio frontend."""
    taken: list[int] = []
    backend_port = cfg.find_free_port(cfg.BACKEND_PORT_START, exclude=taken)
    taken.append(backend_port)
    mcp_port = cfg.find_free_port(cfg.MCP_PORT_START, exclude=taken)
    taken.append(mcp_port)
    gradio_port = cfg.find_free_port(cfg.GRADIO_PORT_START, exclude=taken)
    return backend_port, mcp_port, gradio_port


# ─────────────────────────── FastAPI application ──────────────────────────────

def build_fastapi_app(
    mentor_engine: Any,
    memory_manager: Any,
    curriculum_engine: Any,
    mcp_executor: Any,
    mcp_port: int,
) -> Any:
    """Build and return the FastAPI application."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi import WebSocket

    from api.routes import init_routes, router as api_router
    from api.websocket import init_websocket, websocket_chat_handler
    from mcp.server import create_mcp_app

    init_routes(mentor_engine, memory_manager, curriculum_engine)
    init_websocket(mentor_engine, memory_manager)

    app = FastAPI(
        title="Skython AI Backend",
        description="Backend API for Skython AI offline Python mentor",
        version="1.0.0",
    )

    # CORS — only localhost origins
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    # WebSocket
    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket) -> None:
        await websocket_chat_handler(websocket)

    # Mount MCP sub-app
    mcp_app = create_mcp_app(mcp_executor)
    app.mount("/mcp_internal", mcp_app)  # Internal mount

    return app


# ─────────────────────────── Server threads ───────────────────────────────────

def start_backend_server(app: Any, port: int) -> None:
    """Start uvicorn in a daemon thread."""
    import uvicorn
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="uvicorn-backend")
    thread.start()
    log.info("✅ Backend server starting on port %d", port)
    time.sleep(1.5)  # Give uvicorn time to bind


def start_mcp_server(mcp_executor: Any, port: int) -> None:
    """Start a separate MCP uvicorn server in a daemon thread."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    from mcp.server import create_mcp_app

    mcp_app = create_mcp_app(mcp_executor)

    # Add CORS
    standalone = FastAPI()
    standalone.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    standalone.mount("/", mcp_app)

    config = uvicorn.Config(
        app=standalone,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="uvicorn-mcp")
    thread.start()
    log.info("✅ MCP server starting on port %d", port)
    time.sleep(1.0)


# ─────────────────────────── Skill registration ───────────────────────────────

def register_skills() -> None:
    """Register all teaching skills in the global registry."""
    from skills.analogy_skill import analogy_handler
    from skills.code_trace_skill import code_trace_handler
    from skills.hint_skill import hint_handler
    from skills.rubber_duck_skill import rubber_duck_handler
    from skills.registry import Skill, get_registry

    registry = get_registry()
    registry.register(Skill("analogy_first", "Analogy-based teaching for beginners", analogy_handler))
    registry.register(Skill("code_trace", "Step-by-step code tracing", code_trace_handler))
    registry.register(Skill("rubber_duck", "Rubber duck debugging method", rubber_duck_handler))
    registry.register(Skill("hints", "Progressive 3-tier hint system", lambda **kw: hint_handler(**kw)))

    log.info("✅ Skill Registry loaded: %d skills", len(registry))


# ─────────────────────────── Success banner ───────────────────────────────────

def print_success_banner(fport: int, bport: int, mport: int) -> None:
    msg = (
        f"\n+================================================+\n"
        f"|   SKYTHON AI is running!                       |\n"
        f"|   Frontend:  http://localhost:{fport:<5}           |\n"
        f"|   Backend:   http://localhost:{bport:<5}           |\n"
        f"|   MCP:       http://localhost:{mport:<5}           |\n"
        f"+================================================+\n"
    )
    print(msg)


# ─────────────────────────── Main ─────────────────────────────────────────────

def main() -> None:
    print_banner()
    log.info("Starting Skython AI...")

    # ── Step 1: Python version ────────────────────────────────────────────────
    log.info("✅ Python %s.%s.%s", *sys.version_info[:3])

    # ── Step 2: Find ports ────────────────────────────────────────────────────
    backend_port, mcp_port, gradio_port = find_ports()
    log.info("Ports → Backend:%d  MCP:%d  Gradio:%d", backend_port, mcp_port, gradio_port)

    # ── Step 3: Initialize database ───────────────────────────────────────────
    from database.db import init_db
    init_db()

    # ── Step 4: Check Ollama ──────────────────────────────────────────────────
    from llm.ollama_adapter import OllamaAdapter
    llm = OllamaAdapter()

    if llm.is_available():
        log.info("✅ Ollama online — model: %s", llm.model_name)
    else:
        log.warning("⚠️ Ollama not running. LLM features will be unavailable.")
        log.warning("   Start Ollama with: ollama serve")
        log.warning("   Pull model with:   ollama pull gemma3:1b")

    # ── Step 5: Register skills ───────────────────────────────────────────────
    register_skills()

    # ── Step 6: Initialize core engines ──────────────────────────────────────
    from engines.memory_manager import MemoryManager
    from engines.curriculum_engine import CurriculumEngine
    from engines.mentor_engine import MentorEngine

    memory = MemoryManager()
    curriculum = CurriculumEngine(memory)
    mentor = MentorEngine(llm, memory)

    if mentor.is_ready():
        log.info("✅ Mentor Engine ready")
    else:
        log.warning("⚠️ Mentor Engine not fully ready (LLM may be offline)")

    # ── Step 7: Build MCP executor ────────────────────────────────────────────
    from engines.code_analysis import analyze
    from engines.sandbox import execute_code
    from engines.teaching_engine import TeachingEngine
    from mcp.tools import MCPToolExecutor

    teaching = TeachingEngine(llm)
    mcp_executor = MCPToolExecutor(
        memory_manager=memory,
        curriculum_engine=curriculum,
        sandbox_execute=execute_code,
        analyze_code=analyze,
        teaching_engine=teaching,
    )

    # ── Step 8: Start FastAPI backend ────────────────────────────────────────
    fastapi_app = build_fastapi_app(mentor, memory, curriculum, mcp_executor, mcp_port)
    start_backend_server(fastapi_app, backend_port)

    # ── Step 9: Start MCP server ──────────────────────────────────────────────
    start_mcp_server(mcp_executor, mcp_port)

    # ── Step 10: Build and launch Gradio UI ───────────────────────────────────
    from ui.dashboard import build_ui

    demo, css, theme = build_ui(
        mentor_engine=mentor,
        memory_manager=memory,
        curriculum_engine=curriculum,
        llm_adapter=llm,
        mcp_executor=mcp_executor,
        backend_port=backend_port,
        mcp_port=mcp_port,
        gradio_port=gradio_port,
    )

    print_success_banner(gradio_port, backend_port, mcp_port)

    demo.launch(
        server_name="127.0.0.1",
        server_port=gradio_port,
        share=False,
        quiet=True,
        inbrowser=True,
        css=css,
        theme=theme,
    )


if __name__ == "__main__":
    main()
