"""
ui/dashboard.py — Main Gradio UI dashboard (6 tabs)
"""

from __future__ import annotations

import json
import logging
import base64
import os
from typing import Any

import gradio as gr

from ui.components import SKYTHON_CSS, format_topic_card_html, mastery_emoji

log = logging.getLogger(__name__)

# ─────────────────────────── State ────────────────────────────────────────────
# Shared references injected at startup
_mentor_engine: Any = None
_memory_manager: Any = None
_curriculum_engine: Any = None
_llm_adapter: Any = None
_mcp_executor: Any = None
_backend_port: int = 8000
_mcp_port: int = 8001


def init_dashboard(
    mentor_engine: Any,
    memory_manager: Any,
    curriculum_engine: Any,
    llm_adapter: Any,
    mcp_executor: Any,
    backend_port: int,
    mcp_port: int,
) -> None:
    global _mentor_engine, _memory_manager, _curriculum_engine
    global _llm_adapter, _mcp_executor, _backend_port, _mcp_port
    _mentor_engine = mentor_engine
    _memory_manager = memory_manager
    _curriculum_engine = curriculum_engine
    _llm_adapter = llm_adapter
    _mcp_executor = mcp_executor
    _backend_port = backend_port
    _mcp_port = mcp_port


# ─────────────────────────── Session state ────────────────────────────────────

_active_sessions: dict[str, dict[str, Any]] = {}  # student_name → session info


def _get_or_create_session(student_name: str) -> dict[str, Any]:
    """Return or create a session dict for a student."""
    if student_name not in _active_sessions:
        student = _memory_manager.get_or_create_student(student_name)
        session = _memory_manager.create_session(student.id)
        _active_sessions[student_name] = {
            "student_id": student.id,
            "session_id": session.id,
            "current_topic": session.active_topic or "variables",
            "hint_level": 0,
            "strategy": "general",
        }
    return _active_sessions[student_name]


# ─────────────────────────── Tab 1: Mentor Chat ───────────────────────────────

def _chat_respond(
    message: str,
    history: list[dict],
    student_name: str,
) -> tuple[list[dict], str, str, str, str]:
    """Process a chat message and return updated history + sidebar state."""
    if not message.strip():
        return history, "", _sidebar_topic(student_name), _sidebar_hint(student_name), _sidebar_strategy(student_name)

    if not student_name.strip():
        student_name = "Student"

    sess = _get_or_create_session(student_name)

    try:
        response = _mentor_engine.process_input(
            student_id=sess["student_id"],
            session_id=sess["session_id"],
            user_input=message,
        )
        # Update local cache
        sess["current_topic"] = response.current_topic
        sess["hint_level"] = response.hint_level
        sess["strategy"] = response.strategy_used

        bot_msg = response.content

        # If code was submitted, append execution result
        if response.code_result:
            cr = response.code_result
            if cr.get("stdout"):
                bot_msg += f"\n\n**Output:**\n```\n{cr['stdout']}\n```"
            if cr.get("stderr") and not cr.get("success"):
                bot_msg += f"\n\n**Error:**\n```\n{cr['stderr']}\n```"

    except Exception as exc:
        log.error("Chat error: %s", exc)
        bot_msg = f"⚠️ An error occurred: {exc}"

    # Gradio 6.x uses messages dict format: {"role": str, "content": str}
    history = list(history) + [
        {"role": "user", "content": f"👤 {message}"},
        {"role": "assistant", "content": f"🤖 {bot_msg}"},
    ]
    return (
        history,
        "",  # clear input
        _sidebar_topic(student_name),
        _sidebar_hint(student_name),
        _sidebar_strategy(student_name),
    )


def _quick_command(cmd: str, history: list[dict], student_name: str) -> tuple:
    return _chat_respond(cmd, history, student_name)


def _load_chat_history(student_name: str) -> tuple[list[dict], str, str, str]:
    if not student_name.strip():
        student_name = "Student"
    
    sess = _get_or_create_session(student_name)
    history_dicts = _memory_manager.get_context(sess["session_id"], n=50)
    
    history = []
    for msg in history_dicts:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "student":
            history.append({"role": "user", "content": f"👤 {content}"})
        elif role == "mentor":
            history.append({"role": "assistant", "content": f"🤖 {content}"})
            
    return (
        history,
        _sidebar_topic(student_name),
        _sidebar_hint(student_name),
        _sidebar_strategy(student_name),
    )


def _sidebar_topic(student_name: str) -> str:
    sess = _active_sessions.get(student_name)
    if not sess:
        return "📚 **Current Topic:** `variables`"
    topic = sess.get("current_topic", "variables")
    return f"📚 **Current Topic:** `{topic}`"


def _sidebar_hint(student_name: str) -> str:
    sess = _active_sessions.get(student_name)
    if not sess:
        return "💡 **Hints:** ○○○"
    level = sess.get("hint_level", 0)
    dots = "●" * level + "○" * (3 - level)
    return f"💡 **Hints:** {dots} ({level}/3)"


def _sidebar_strategy(student_name: str) -> str:
    sess = _active_sessions.get(student_name)
    if not sess:
        return "🧠 **Strategy:** general"
    strategy = sess.get("strategy", "general")
    return f"🧠 **Strategy:** {strategy.replace('_', ' ')}"


def build_chat_tab() -> None:
    with gr.Tab("💬 Mentor Chat"):
        gr.HTML("""
        <div style="text-align: center; margin-bottom: 20px; padding: 10px;">
            <h1 style="color: #58a6ff; font-size: 2.5rem; font-weight: 700; margin-bottom: 5px;">🎓 Skython AI</h1>
            <p style="color: #3b82f6; font-size: 1.1rem; font-weight: 500; letter-spacing: 0.5px;">Learn Python Locally, Code Smarter — Your Offline No-Cloud Mentor</p>
        </div>
        """)

        with gr.Row():
            # ── Main chat area ────────────────────────────────────────────
            with gr.Column(scale=3):
                student_name_input = gr.Textbox(
                    label="👤 Your Name",
                    placeholder="Enter your name to start...",
                    value="Student",
                    max_lines=1,
                    elem_id="student-name-input",
                )

                chatbot = gr.Chatbot(
                    label="Skython Mentor Chat",
                    height=480,
                    show_label=False,
                    elem_id="main-chatbot",
                    avatar_images=(None, None),
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Ask a question or paste your Python code...",
                        label="",
                        scale=4,
                        lines=2,
                        max_lines=8,
                        show_label=False,
                        elem_id="message-input",
                    )
                    send_btn = gr.Button("Send ▶", variant="primary", scale=1, min_width=80)

                # Quick action chips
                with gr.Row():
                    hint_btn = gr.Button("💡 /hint", size="sm", variant="secondary")
                    status_btn = gr.Button("📊 /status", size="sm", variant="secondary")
                    topic_btn = gr.Button("📚 /topic", size="sm", variant="secondary")
                    skip_btn = gr.Button("⏭️ /skip", size="sm", variant="secondary")
                    help_btn = gr.Button("❓ /help", size="sm", variant="secondary")

            # ── Sidebar ────────────────────────────────────────────────────
            with gr.Column(scale=1, elem_classes=["sidebar-panel", "white-text"]):
                gr.Markdown("### 📌 Session Info")

                topic_display = gr.Markdown(_sidebar_topic("Student"))
                hint_display = gr.Markdown(_sidebar_hint("Student"))
                strategy_display = gr.Markdown(_sidebar_strategy("Student"))

                gr.HTML("<hr style='border-color:#30363d;margin:12px 0'>")

                gr.Markdown("""
                ### 💡 Tips
                - Type naturally — I'll detect code vs questions
                - Use `/hint` up to 3 times per problem
                - Paste your full code for analysis
                - Ask "why" — I love Socratic questions!
                """)

                llm_status = gr.HTML(_render_llm_status())
                gr.Button("🔄 Check LLM", size="sm").click(
                    fn=_render_llm_status, outputs=llm_status
                )

        # ── Wire up events ─────────────────────────────────────────────────
        send_outputs = [chatbot, msg_input, topic_display, hint_display, strategy_display]

        send_btn.click(
            fn=_chat_respond,
            inputs=[msg_input, chatbot, student_name_input],
            outputs=send_outputs,
        )
        msg_input.submit(
            fn=_chat_respond,
            inputs=[msg_input, chatbot, student_name_input],
            outputs=send_outputs,
        )

        load_outputs = [chatbot, topic_display, hint_display, strategy_display]
        student_name_input.submit(
            fn=_load_chat_history,
            inputs=[student_name_input],
            outputs=load_outputs,
        )
        student_name_input.blur(
            fn=_load_chat_history,
            inputs=[student_name_input],
            outputs=load_outputs,
        )

        for btn, cmd in [
            (hint_btn, "/hint"),
            (status_btn, "/status"),
            (topic_btn, "/topic"),
            (skip_btn, "/skip"),
            (help_btn, "/help"),
        ]:
            btn.click(
                fn=lambda h, n, c=cmd: _quick_command(c, h, n),
                inputs=[chatbot, student_name_input],
                outputs=send_outputs,
            )


def _render_llm_status() -> str:
    try:
        online = _llm_adapter.is_available() if _llm_adapter else False
        model = _llm_adapter.model_name if _llm_adapter else "N/A"
    except Exception:
        online = False
        model = "N/A"

    icon = "🟢" if online else "🔴"
    status = "Online" if online else "Offline"
    return f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-top:12px">
        <div style="font-size:12px;color:#ffffff;margin-bottom:4px">LLM Status</div>
        <div style="font-weight:600;color:#ffffff;">{icon} {status}</div>
        <div style="font-size:11px;color:#ffffff;margin-top:4px">{model}</div>
    </div>
    """


# ─────────────────────────── Tab 2: Dashboard ────────────────────────────────

def build_dashboard_tab() -> None:
    with gr.Tab("📊 Student Dashboard"):
        with gr.Row():
            dash_name = gr.Textbox(label="👤 Student Name", value="Student", max_lines=1)
            refresh_btn = gr.Button("🔄 Refresh", variant="secondary")

        profile_html = gr.HTML(_render_profile("Student"))
        mastery_html = gr.HTML(_render_mastery_grid("Student"))

        with gr.Row():
            with gr.Column():
                stats_html = gr.HTML(_render_stats("Student"))
            with gr.Column():
                misconceptions_html = gr.HTML(_render_misconceptions("Student"))

        def refresh_all(name: str) -> tuple:
            return (
                _render_profile(name),
                _render_mastery_grid(name),
                _render_stats(name),
                _render_misconceptions(name),
            )

        refresh_btn.click(
            fn=refresh_all,
            inputs=dash_name,
            outputs=[profile_html, mastery_html, stats_html, misconceptions_html],
        )
        dash_name.submit(
            fn=refresh_all,
            inputs=dash_name,
            outputs=[profile_html, mastery_html, stats_html, misconceptions_html],
        )


def _render_profile(student_name: str) -> str:
    try:
        student = _memory_manager.get_or_create_student(student_name)
        summary = _memory_manager.get_student_summary(student.id)
        info = summary.get("student", {})
        return f"""
        <div class="skython-card">
            <h3 style="margin:0 0 8px 0;color:#58a6ff">👤 {info.get('name', student_name)}</h3>
            <div style="display:flex;gap:12px;flex-wrap:wrap">
                <span class="badge badge-cyan">Level: {info.get('experience_level','novice').title()}</span>
                <span class="badge badge-green">Velocity: {info.get('learning_velocity','normal').title()}</span>
                <span class="badge badge-gray">Member since: {info.get('created_at','')[:10]}</span>
            </div>
        </div>
        """
    except Exception as exc:
        return f"<p style='color:#f85149'>Error loading profile: {exc}</p>"


def _render_mastery_grid(student_name: str) -> str:
    try:
        student = _memory_manager.get_or_create_student(student_name)
        mastery_map = _curriculum_engine.get_mastery_map(student.id)
        cards = "".join(
            format_topic_card_html(tid, info)
            for tid, info in mastery_map.items()
        )
        return f"""
        <div class="skython-card">
            <h3 style="margin:0 0 16px 0;color:#e6edf3">🗺️ Mastery Map</h3>
            <div class="topic-grid">{cards}</div>
            <div style="margin-top:16px;font-size:12px;color:#8b949e">
                🔒 Locked &nbsp; 🔵 Unlocked &nbsp; 🟡 In Progress &nbsp; 🟢 Mastered &nbsp; ⭐ Expert
            </div>
        </div>
        """
    except Exception as exc:
        return f"<p style='color:#f85149'>Error: {exc}</p>"


def _render_stats(student_name: str) -> str:
    try:
        student = _memory_manager.get_or_create_student(student_name)
        summary = _memory_manager.get_student_summary(student.id)
        mastery = summary.get("mastery", [])
        total_success = sum(m["successful"] for m in mastery)
        total_failed = sum(m["failed"] for m in mastery)
        topics_started = len(mastery)
        sessions = summary.get("total_sessions", 0)
        return f"""
        <div class="skython-card">
            <h4 style="margin:0 0 12px 0;color:#e6edf3">📈 Session Statistics</h4>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                <div style="text-align:center;background:#0d1117;border-radius:8px;padding:12px">
                    <div style="font-size:24px;font-weight:700;color:#58a6ff">{sessions}</div>
                    <div style="font-size:12px;color:#8b949e">Total Sessions</div>
                </div>
                <div style="text-align:center;background:#0d1117;border-radius:8px;padding:12px">
                    <div style="font-size:24px;font-weight:700;color:#3fb950">{total_success}</div>
                    <div style="font-size:12px;color:#8b949e">Exercises Passed</div>
                </div>
                <div style="text-align:center;background:#0d1117;border-radius:8px;padding:12px">
                    <div style="font-size:24px;font-weight:700;color:#f85149">{total_failed}</div>
                    <div style="font-size:12px;color:#8b949e">Exercises Failed</div>
                </div>
                <div style="text-align:center;background:#0d1117;border-radius:8px;padding:12px">
                    <div style="font-size:24px;font-weight:700;color:#bc8cff">{topics_started}</div>
                    <div style="font-size:12px;color:#8b949e">Topics Started</div>
                </div>
            </div>
        </div>
        """
    except Exception as exc:
        return f"<p style='color:#f85149'>Error: {exc}</p>"


def _render_misconceptions(student_name: str) -> str:
    try:
        student = _memory_manager.get_or_create_student(student_name)
        summary = _memory_manager.get_student_summary(student.id)
        items = summary.get("misconceptions", [])
        if not items:
            return """
            <div class="skython-card">
                <h4 style="margin:0 0 12px 0;color:#e6edf3">⚡ Misconceptions</h4>
                <p style="color:#8b949e">No misconceptions recorded yet. Great job! 🎉</p>
            </div>
            """
        rows = ""
        for mc in items:
            corrected = "✅" if mc.get("corrected") else "❌"
            rows += f"""
            <tr>
                <td><code>{mc.get('topic_id','?')}</code></td>
                <td style="font-size:12px">{mc.get('description','')[:60]}...</td>
                <td style="text-align:center">{mc.get('frequency',1)}x</td>
                <td style="text-align:center">{corrected}</td>
            </tr>
            """
        return f"""
        <div class="skython-card">
            <h4 style="margin:0 0 12px 0;color:#e6edf3">⚡ Misconceptions Tracker</h4>
            <table>
                <thead><tr>
                    <th>Topic</th><th>Description</th><th>Freq</th><th>Fixed</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """
    except Exception as exc:
        return f"<p style='color:#f85149'>Error: {exc}</p>"


# ─────────────────────────── Tab 3: Python Sandbox ───────────────────────────

def build_sandbox_tab() -> None:
    with gr.Tab("🐍 Python Sandbox"):
        gr.HTML("""
        <div class="skython-card">
            <h3 style="margin:0 0 8px 0;color:#58a6ff">🎓 Python Sandbox</h3>
            <p style="color:#8b949e;margin:0">
                Secure execution environment — dangerous imports are blocked. Run code safely!
            </p>
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=3):
                code_editor = gr.Code(
                    label="Python Code Editor",
                    language="python",
                    lines=16,
                    value='# Write your Python code here\nprint("Hello, Skython! 🐍")\n\n# Try: list comprehension, functions, loops...\nnumbers = [1, 2, 3, 4, 5]\nsquares = [n**2 for n in numbers]\nprint(f"Squares: {squares}")',
                    elem_id="code-editor",
                )

                with gr.Row():
                    run_btn = gr.Button("▶️ Run Code", variant="primary", scale=2)
                    ask_btn = gr.Button("💬 Ask Mentor", variant="secondary", scale=1)

            with gr.Column(scale=2):
                security_status = gr.HTML("""
                <div style="background:#1a3a22;border:1px solid #238636;border-radius:8px;padding:10px;margin-bottom:12px">
                    <strong>✅ Sandbox Active</strong>
                    <div style="font-size:12px;color:#8b949e;margin-top:4px">
                        Blocked: os, sys, subprocess, socket, eval, exec, open
                    </div>
                </div>
                """)

                stdout_output = gr.HTML(
                    "<div class='sandbox-stdout' style='min-height:80px'>Output will appear here...</div>"
                )
                stderr_output = gr.HTML("")
                exec_time = gr.HTML("")

        def run_code(code: str) -> tuple:
            from engines.sandbox import execute_code
            result = execute_code(code)

            if result.error_type == "SecurityViolation":
                sec_html = """
                <div style="background:#3a1a1a;border:1px solid #da3633;border-radius:8px;padding:10px;margin-bottom:12px">
                    <strong>⚠️ Security Violation</strong>
                    <div style="font-size:12px;color:#8b949e;margin-top:4px">Blocked import or builtin detected.</div>
                </div>
                """
            else:
                sec_html = """
                <div style="background:#1a3a22;border:1px solid #238636;border-radius:8px;padding:10px;margin-bottom:12px">
                    <strong>✅ Sandbox Active</strong>
                    <div style="font-size:12px;color:#8b949e;margin-top:4px">Blocked: os, sys, subprocess, socket, eval, exec, open</div>
                </div>
                """

            stdout_html = f"<div class='sandbox-stdout'>{result.stdout or '(no output)'}</div>"
            stderr_html = (
                f"<div class='sandbox-stderr'>{result.stderr}</div>"
                if result.stderr
                else ""
            )
            time_html = (
                f"<div style='font-size:12px;color:#8b949e;margin-top:8px'>⏱ {result.execution_time:.3f}s · "
                f"Return code: {result.return_code}</div>"
            )
            return sec_html, stdout_html, stderr_html, time_html

        run_btn.click(
            fn=run_code,
            inputs=code_editor,
            outputs=[security_status, stdout_output, stderr_output, exec_time],
        )


# ─────────────────────────── Tab 4: Curriculum Map ───────────────────────────

def build_curriculum_tab() -> None:
    with gr.Tab("📚 Curriculum Map"):
        with gr.Row():
            curr_name = gr.Textbox(label="👤 Student Name", value="Student", max_lines=1)
            curr_refresh = gr.Button("🔄 Refresh", variant="secondary")

        curriculum_html = gr.HTML(_render_curriculum("Student"))

        def refresh_curriculum(name: str) -> str:
            return _render_curriculum(name)

        curr_refresh.click(fn=refresh_curriculum, inputs=curr_name, outputs=curriculum_html)
        curr_name.submit(fn=refresh_curriculum, inputs=curr_name, outputs=curriculum_html)


def _render_curriculum(student_name: str) -> str:
    try:
        student = _memory_manager.get_or_create_student(student_name)
        mastery_map = _curriculum_engine.get_mastery_map(student.id)
        next_topic = _curriculum_engine.get_next_topic(student.id)

        # Group by difficulty
        by_difficulty: dict[int, list[tuple[str, dict]]] = {}
        for tid, info in mastery_map.items():
            d = info["difficulty"]
            by_difficulty.setdefault(d, []).append((tid, info))

        difficulty_labels = {1: "Foundations", 2: "Building Blocks", 3: "Intermediate", 4: "Advanced"}

        html_parts = [f"""
        <div class="skython-card">
            <h3 style="margin:0 0 8px 0;color:#58a6ff">📚 Curriculum Map</h3>
            <p style="color:#8b949e;margin:0 0 16px 0">
                Recommended next: <strong style="color:#d29922">{next_topic or 'All completed! 🎉'}</strong>
            </p>
        """]

        for diff in sorted(by_difficulty.keys()):
            label = difficulty_labels.get(diff, f"Level {diff}")
            html_parts.append(f"<h4 style='color:#8b949e;margin:16px 0 8px 0;font-size:13px;text-transform:uppercase;letter-spacing:1px'>{label}</h4>")
            html_parts.append('<div class="topic-grid">')
            for tid, info in sorted(by_difficulty[diff]):
                highlighted = ' style="border-color:#d29922;box-shadow:0 0 15px rgba(210,153,34,0.3)"' if tid == next_topic else ""
                level = info.get("mastery_level", "locked")
                score = info.get("score", 0.0)
                locked = info.get("locked", True)
                prereqs = info.get("prerequisites", [])
                pct = int(score * 100)
                emoji = mastery_emoji(level)
                lock_class = "locked" if locked else ""
                prereq_str = f"Requires: {', '.join(prereqs)}" if prereqs else "No prerequisites"

                html_parts.append(f"""
                <div class="topic-card {lock_class}"{highlighted}>
                    <div class="topic-name">{emoji} {tid.replace('_',' ').title()}</div>
                    <div class="topic-level">{prereq_str}</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:{pct}%"></div>
                    </div>
                    <div style="font-size:11px;color:#8b949e;margin-top:4px">{level.title()} — {pct}%</div>
                </div>
                """)
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "".join(html_parts)

    except Exception as exc:
        return f"<p style='color:#f85149'>Error: {exc}</p>"


# ─────────────────────────── Tab 5: MCP Server ───────────────────────────────

def build_mcp_tab() -> None:
    from ui.mcp_ui import build_mcp_tab as _build
    _build(_mcp_port, _mcp_executor)


# ─────────────────────────── Tab 6: Settings ─────────────────────────────────

def build_settings_tab() -> None:
    with gr.Tab("⚙️ Settings"):
        gr.HTML("""
        <div class="skython-card">
            <h3 style="margin:0 0 8px 0;color:#58a6ff">⚙️ Settings</h3>
        </div>
        """)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🤖 Model Configuration")
                model_dropdown = gr.Dropdown(
                    label="Active Model",
                    choices=["gemma3:1b", "gemma3:4b", "llama3.2:1b", "mistral"],
                    value="gemma3:1b",
                )
                check_ollama_btn = gr.Button("🔍 Check Ollama Status", variant="secondary")
                ollama_status = gr.HTML(_check_ollama_status())

                check_ollama_btn.click(fn=_check_ollama_status, outputs=ollama_status)

                def refresh_models() -> list[str]:
                    try:
                        models = _llm_adapter.list_models()
                        return gr.Dropdown(choices=models or ["gemma3:1b"])
                    except Exception:
                        return gr.Dropdown(choices=["gemma3:1b"])

                gr.Button("🔄 Refresh Model List", size="sm").click(
                    fn=refresh_models, outputs=model_dropdown
                )

            with gr.Column():
                gr.Markdown("### 💾 Data Management")

                def export_data(student_name: str) -> str:
                    try:
                        student = _memory_manager.get_or_create_student(student_name)
                        summary = _memory_manager.get_student_summary(student.id)
                        return json.dumps(summary, indent=2, default=str)
                    except Exception as exc:
                        return f"Error: {exc}"

                export_name = gr.Textbox(label="Student Name for Export", value="Student")
                export_btn = gr.Button("📥 Export Student Data", variant="secondary")
                export_output = gr.Code(label="Exported Data (JSON)", language="json", lines=10)
                export_btn.click(fn=export_data, inputs=export_name, outputs=export_output)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📋 Application Logs")
                log_output = gr.Textbox(
                    label="Recent Logs (last 50 lines)",
                    lines=12,
                    interactive=False,
                )

                def load_logs() -> str:
                    try:
                        from config import LOG_PATH
                        if LOG_PATH.exists():
                            lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
                            return "\n".join(lines[-50:])
                        return "No log file yet."
                    except Exception as exc:
                        return f"Error reading logs: {exc}"

                gr.Button("🔄 Refresh Logs", size="sm").click(fn=load_logs, outputs=log_output)
                load_logs()  # Load on startup


def _check_ollama_status() -> str:
    try:
        online = _llm_adapter.is_available() if _llm_adapter else False
        models = _llm_adapter.list_models() if _llm_adapter and online else []
        model_name = _llm_adapter.model_name if _llm_adapter else "N/A"
        icon = "🟢" if online else "🔴"
        status = "Online" if online else "Offline"
        model_list = ", ".join(models[:5]) if models else "None"
        return f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-top:8px">
            <div style="font-weight:600;margin-bottom:8px">{icon} Ollama {status}</div>
            <div style="font-size:13px;color:#8b949e">Active model: <code>{model_name}</code></div>
            <div style="font-size:13px;color:#8b949e">Available: {model_list}</div>
            {"<div style='margin-top:8px;font-size:12px;color:#f85149'>⚠️ Run: <code>ollama serve</code> to start Ollama</div>" if not online else ""}
        </div>
        """
    except Exception as exc:
        return f"<p style='color:#f85149'>Error: {exc}</p>"


# ─────────────────────────── Main builder ─────────────────────────────────────

def build_ui(
    mentor_engine: Any,
    memory_manager: Any,
    curriculum_engine: Any,
    llm_adapter: Any,
    mcp_executor: Any,
    backend_port: int,
    mcp_port: int,
    gradio_port: int,
) -> tuple[gr.Blocks, str, Any]:
    """Build and return the full Gradio Blocks application."""
    init_dashboard(
        mentor_engine, memory_manager, curriculum_engine,
        llm_adapter, mcp_executor, backend_port, mcp_port,
    )

    css = SKYTHON_CSS + """
    .tab-nav button { color: #ffffff !important; font-weight: 600 !important; font-size: 14px !important; }
    .tab-nav button.selected { color: #ffffff !important; border-bottom: 2px solid #3b82f6 !important; }
    """

    theme = gr.themes.Base()
    with gr.Blocks() as demo:
        build_chat_tab()
        build_dashboard_tab()
        build_sandbox_tab()
        build_curriculum_tab()
        build_mcp_tab()
        build_settings_tab()

    return demo, css, theme
