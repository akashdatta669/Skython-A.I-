"""
ui/components.py — Reusable Gradio UI building blocks and CSS theme
"""

from __future__ import annotations

# ─────────────────────────── CSS Theme ────────────────────────────────────────

SKYTHON_CSS = """
/* ── Skython AI Theme ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-card: #1c2128;
    --bg-card-hover: #21262d;
    --accent-cyan: #58a6ff;
    --accent-green: #3fb950;
    --accent-yellow: #d29922;
    --accent-purple: #bc8cff;
    --accent-red: #f85149;
    --accent-orange: #e3b341;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #484f58;
    --border: #30363d;
    --border-active: #58a6ff;
    --success: #238636;
    --warning: #9e6a03;
    --error: #da3633;
}

body, .gradio-container {
    background-color: #0d1117 !important;
    background-image: 
        radial-gradient(1px 1px at 25px 5px, white, transparent),
        radial-gradient(1px 1px at 50px 25px, white, transparent),
        radial-gradient(1px 1px at 125px 20px, white, transparent),
        radial-gradient(1.5px 1.5px at 50px 75px, white, transparent),
        radial-gradient(2px 2px at 15px 125px, white, transparent),
        radial-gradient(2.5px 2.5px at 110px 80px, white, transparent) !important;
    background-size: 200px 200px !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: var(--text-primary) !important;
}

/* Tabs */
.tab-nav button {
    background: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    padding: 10px 18px !important;
}
.tab-nav button.selected {
    background: var(--bg-card) !important;
    color: var(--accent-cyan) !important;
    border-bottom-color: var(--bg-card) !important;
}
.tab-nav button:hover:not(.selected) {
    color: var(--text-primary) !important;
    background: var(--bg-card-hover) !important;
}

/* Chat */
.chatbot {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
.chatbot .message.user {
    background: #1a3a5c !important;
    border-radius: 12px 12px 4px 12px !important;
}
.chatbot .message.bot {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px 12px 12px 4px !important;
}
.chatbot .message {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    color: var(--text-primary) !important;
}
.chatbot .message code {
    font-family: 'JetBrains Mono', monospace !important;
    background: #0d1117 !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 13px !important;
}
.chatbot .message pre {
    background: #0d1117 !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 12px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* Inputs */
textarea, input[type="text"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}
textarea:focus, input:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
}

/* Buttons */
button.primary {
    background: linear-gradient(135deg, #1d6fa5, #58a6ff) !important;
    border: none !important;
    border-radius: 8px !important;
    color: white !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 15px rgba(88,166,255,0.35) !important;
}
button.secondary {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
button.secondary:hover {
    border-color: var(--accent-cyan) !important;
    color: var(--accent-cyan) !important;
}

/* Code editor */
.code-editor {
    background: #0d1117 !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
}

/* Cards */
.skython-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}
.skython-card:hover {
    border-color: var(--border-active);
    box-shadow: 0 0 15px rgba(88,166,255,0.1);
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-cyan   { background: #1d3a5c; color: #58a6ff; border: 1px solid #58a6ff44; }
.badge-green  { background: #1a3a22; color: #3fb950; border: 1px solid #3fb95044; }
.badge-yellow { background: #3a2a00; color: #d29922; border: 1px solid #d2992244; }
.badge-red    { background: #3a1a1a; color: #f85149; border: 1px solid #f8514944; }
.badge-gray   { background: #22272e; color: #8b949e; border: 1px solid #30363d; }

/* Mastery colors */
.mastery-expert       { color: #ffd700; }
.mastery-advanced     { color: #3fb950; }
.mastery-intermediate { color: #58a6ff; }
.mastery-beginner     { color: #d29922; }
.mastery-novice       { color: #f85149; }
.mastery-locked       { color: #484f58; }

/* Header banner */
.skython-header {
    background: linear-gradient(135deg, #0d1117 0%, #1a2332 50%, #0d1117 100%);
    border: 1px solid #1d6fa544;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    text-align: center;
}
.skython-header h1 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #58a6ff, #bc8cff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
}
.skython-header p {
    color: var(--text-secondary);
    margin: 8px 0 0 0;
    font-size: 14px;
}

/* Sidebar */
.sidebar-panel {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
}
.white-text, .white-text * {
    color: #ffffff !important;
}

/* Topic grid */
.topic-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 16px;
}
.topic-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    transition: all 0.2s ease;
    cursor: pointer;
}
.topic-card:hover {
    border-color: var(--accent-cyan);
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(88,166,255,0.15);
}
.topic-card.locked {
    opacity: 0.4;
    cursor: not-allowed;
}
.topic-card .topic-name {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 6px;
}
.topic-card .topic-level {
    font-size: 12px;
    color: var(--text-secondary);
}

/* Progress bar */
.progress-bar {
    background: var(--bg-secondary);
    border-radius: 6px;
    height: 8px;
    overflow: hidden;
    margin: 8px 0;
}
.progress-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #1d6fa5, #58a6ff);
    transition: width 0.5s ease;
}

/* Sandbox output */
.sandbox-stdout {
    background: #0d1f0d;
    border: 1px solid #238636;
    border-radius: 8px;
    padding: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #3fb950;
    white-space: pre-wrap;
}
.sandbox-stderr {
    background: #1f0d0d;
    border: 1px solid #da3633;
    border-radius: 8px;
    padding: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #f85149;
    white-space: pre-wrap;
}

/* MCP monitor */
.mcp-tool-row {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
}
.mcp-status-online  { color: #3fb950; }
.mcp-status-offline { color: #f85149; }

/* Quick action chips */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.chip {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
}
.chip:hover {
    border-color: var(--accent-cyan);
    color: var(--accent-cyan);
    background: #1a2840;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* Animations */
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 5px rgba(88,166,255,0.3); }
    50% { box-shadow: 0 0 20px rgba(88,166,255,0.6); }
}
.pulse { animation: pulse-glow 2s ease-in-out infinite; }

@keyframes slide-in {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.slide-in { animation: slide-in 0.3s ease-out; }

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
th {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
}
td {
    padding: 10px 12px;
    border-bottom: 1px solid #21262d;
    color: var(--text-primary);
}
tr:hover td { background: var(--bg-card-hover); }
"""


def mastery_emoji(level: str) -> str:
    """Return an emoji for a mastery level."""
    return {
        "locked": "🔒",
        "unlocked": "🔵",
        "novice": "🟡",
        "beginner": "🟡",
        "intermediate": "🟢",
        "advanced": "🟢",
        "expert": "⭐",
    }.get(level, "⬜")


def format_topic_card_html(topic_id: str, info: dict) -> str:
    """Render a topic card as HTML."""
    level = info.get("mastery_level", "locked")
    score = info.get("score", 0.0)
    locked = info.get("locked", True)
    difficulty = info.get("difficulty", 1)
    prereqs = info.get("prerequisites", [])

    emoji = mastery_emoji(level)
    pct = int(score * 100)
    lock_class = "locked" if locked else ""
    star_str = "⭐" * difficulty

    prereq_str = (
        f"<div class='topic-level'>Requires: {', '.join(prereqs)}</div>"
        if prereqs
        else "<div class='topic-level'>No prerequisites</div>"
    )

    return f"""
<div class="topic-card {lock_class}">
    <div class="topic-name">{emoji} {topic_id.replace('_', ' ').title()}</div>
    <div class="topic-level">Difficulty: {star_str}</div>
    {prereq_str}
    <div class="progress-bar">
        <div class="progress-fill" style="width:{pct}%"></div>
    </div>
    <div style="font-size:11px;color:#8b949e;margin-top:4px">{level.title()} — {pct}%</div>
</div>
"""
