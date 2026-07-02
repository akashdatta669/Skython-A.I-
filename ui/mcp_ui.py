"""
ui/mcp_ui.py — MCP Server monitoring UI tab
"""

from __future__ import annotations

import json
from typing import Any


def build_mcp_tab(mcp_port: int, executor: Any) -> tuple:
    """Build MCP monitor tab contents. Returns gradio components."""
    import gradio as gr

    with gr.Tab("🔌 MCP Server") as tab:
        gr.HTML(f"""
        <div class="skython-card">
            <h3 style="margin:0 0 12px 0;color:#58a6ff">🔌 MCP Server Monitor</h3>
            <p style="color:#8b949e;margin:0">
                Model Context Protocol server — exposes Skython capabilities as tools for AI agents.
            </p>
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=1):
                status_html = gr.HTML(
                    _render_mcp_status(mcp_port, is_running=True),
                    label="Server Status",
                )
                gr.Button("🔄 Refresh Status", size="sm").click(
                    fn=lambda: _render_mcp_status(mcp_port, is_running=True),
                    outputs=status_html,
                )

            with gr.Column(scale=2):
                gr.HTML(_render_tools_table(executor), label="Available Tools")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🧪 Test a Tool")
                tool_select = gr.Dropdown(
                    choices=["get_student_mastery", "execute_python_code", "get_next_topic", "analyze_code", "get_hint"],
                    label="Select Tool",
                    value="execute_python_code",
                )
                params_input = gr.Textbox(
                    label="Parameters (JSON)",
                    value='{"code": "print(\'hello from MCP!\')"}',
                    lines=4,
                    placeholder='{"key": "value"}',
                )
                test_btn = gr.Button("▶️ Execute Tool", variant="primary")
                result_output = gr.Code(label="Tool Result (JSON)", language="json", lines=8)

                def run_tool(tool_name: str, params_str: str) -> str:
                    try:
                        params = json.loads(params_str)
                        result = executor.execute(tool_name, params)
                        return json.dumps(result, indent=2)
                    except json.JSONDecodeError as e:
                        return json.dumps({"error": f"Invalid JSON: {e}"}, indent=2)
                    except Exception as e:
                        return json.dumps({"error": str(e)}, indent=2)

                test_btn.click(
                    fn=run_tool,
                    inputs=[tool_select, params_input],
                    outputs=result_output,
                )

            with gr.Column():
                gr.Markdown("### 📋 cURL Examples")
                curl_examples = gr.HTML(_render_curl_examples(mcp_port))

    return tab


def _render_mcp_status(port: int, is_running: bool) -> str:
    status_icon = "🟢" if is_running else "🔴"
    status_text = "Running" if is_running else "Offline"
    return f"""
    <div class="skython-card">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <span style="font-size:24px">{status_icon}</span>
            <div>
                <div style="font-weight:600;color:#e6edf3">MCP Server — {status_text}</div>
                <div style="color:#8b949e;font-size:13px">http://localhost:{port}</div>
            </div>
        </div>
        <div style="color:#8b949e;font-size:12px">
            Endpoints: <code>GET /mcp/tools</code> · <code>POST /mcp/execute</code>
        </div>
    </div>
    """


def _render_tools_table(executor: Any) -> str:
    from mcp.tools import MCP_TOOLS
    rows = ""
    for tool in MCP_TOOLS:
        params = ", ".join(tool["parameters"].keys())
        rows += f"""
        <tr>
            <td><code style="color:#58a6ff">{tool['name']}</code></td>
            <td style="color:#8b949e;font-size:12px">{tool['description']}</td>
            <td><code style="color:#bc8cff;font-size:11px">{params}</code></td>
        </tr>
        """
    return f"""
    <div class="skython-card">
        <h4 style="margin:0 0 12px 0;color:#e6edf3">Available MCP Tools</h4>
        <table>
            <thead><tr>
                <th>Tool Name</th><th>Description</th><th>Parameters</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """


def _render_curl_examples(port: int) -> str:
    return f"""
    <div class="skython-card">
        <h4 style="margin:0 0 12px 0;color:#e6edf3">cURL Examples</h4>
        <div style="margin-bottom:12px">
            <div style="color:#8b949e;font-size:12px;margin-bottom:6px">List all tools:</div>
            <code style="display:block;background:#0d1117;padding:10px;border-radius:6px;font-size:12px;color:#3fb950">
                curl http://localhost:{port}/mcp/tools
            </code>
        </div>
        <div style="margin-bottom:12px">
            <div style="color:#8b949e;font-size:12px;margin-bottom:6px">Execute code:</div>
            <code style="display:block;background:#0d1117;padding:10px;border-radius:6px;font-size:12px;color:#3fb950">
                curl -X POST http://localhost:{port}/mcp/execute \\<br>
                &nbsp;&nbsp;-H "Content-Type: application/json" \\<br>
                &nbsp;&nbsp;-d '{{"tool":"execute_python_code","parameters":{{"code":"print(1+1)"}}}}'
            </code>
        </div>
        <div>
            <div style="color:#8b949e;font-size:12px;margin-bottom:6px">Analyze code:</div>
            <code style="display:block;background:#0d1117;padding:10px;border-radius:6px;font-size:12px;color:#3fb950">
                curl -X POST http://localhost:{port}/mcp/execute \\<br>
                &nbsp;&nbsp;-H "Content-Type: application/json" \\<br>
                &nbsp;&nbsp;-d '{{"tool":"analyze_code","parameters":{{"code":"for x in lst: lst.remove(x)"}}}}'
            </code>
        </div>
    </div>
    """
