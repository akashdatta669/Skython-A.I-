"""
verify.py — Skython AI verification checklist
Run: python verify.py
All 9 checks must PASS for the build to be considered complete.
"""
import sys

sys.path.insert(0, ".")

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {label}{extra}")


print("\n" + "=" * 60)
print("  SKYTHON AI -- VERIFICATION CHECKLIST")
print("=" * 60)

# -- Check 1: Python version
print("\n[1] Python version")
v = sys.version_info
check("Python >= 3.10", v >= (3, 10), f"Running {v.major}.{v.minor}.{v.micro}")

# -- Check 2: Config
print("\n[2] Config + port scanner")
try:
    import config as cfg
    p = cfg.find_free_port(8000)
    check("config.py imports", True)
    check("find_free_port()", isinstance(p, int), f"port={p}")
except Exception as e:
    check("config.py imports", False, str(e))
    check("find_free_port()", False, str(e))

# -- Check 3: Database
print("\n[3] Database (SQLite + SQLAlchemy)")
try:
    from database.db import init_db, health_check
    init_db()
    ok = health_check()
    check("init_db()", ok)
    check("health_check()", ok)
except Exception as e:
    check("init_db()", False, str(e))
    check("health_check()", False, str(e))

# -- Check 4: Code analysis
print("\n[4] Code analysis engine")
try:
    from engines.code_analysis import analyze
    r_good = analyze("x = 1\nprint(x)\n")
    r_bad = analyze("while True:\n    pass\n")
    check("valid code -> no syntax error", r_good.is_valid_syntax)
    check("infinite loop -> warning detected", r_bad.has_issues, f"warnings={len(r_bad.warnings)}")
except Exception as e:
    check("code_analysis import", False, str(e))

# -- Check 5: Security validator
print("\n[5] Security validator")
try:
    from security.validator import validate_code
    safe, _ = validate_code('print("hello")')
    blocked, violations = validate_code('import os')
    check("safe code passes", safe)
    check("blocked import rejected", not blocked, f"violations={violations}")
except Exception as e:
    check("security validator", False, str(e))

# -- Check 6: Sandbox execution
print("\n[6] Python sandbox execution")
try:
    from engines.sandbox import execute_code
    r = execute_code("print(1 + 1)")
    check("safe code executes", r.success and r.stdout == "2", f"stdout={r.stdout!r}")
    r_blocked = execute_code("import os")
    check("blocked import rejected", not r_blocked.success, f"error_type={r_blocked.error_type}")
except Exception as e:
    check("sandbox execution", False, str(e))

# -- Check 7: Memory manager
print("\n[7] Memory manager (persistence)")
try:
    from engines.memory_manager import MemoryManager
    mm = MemoryManager()
    student = mm.get_or_create_student("Verify_TestStudent_XYZ")
    session = mm.create_session(student.id, "variables")
    mm.save_message(session.id, "student", "what is a variable?", "variables")
    ctx = mm.get_context(session.id)
    check("student create/retrieve", student is not None)
    check("session create", session is not None)
    check("message save + retrieve", len(ctx) == 1, f"messages={len(ctx)}")
    mm.update_mastery(student.id, "variables", True)
    mastery = mm.get_mastery(student.id, "variables")
    check("mastery EMA update", mastery is not None and mastery.score > 0.0, f"score={mastery.score:.3f}")
except Exception as e:
    check("memory manager", False, str(e))

# -- Check 8: Curriculum engine
print("\n[8] Curriculum engine (topic DAG)")
try:
    from engines.curriculum_engine import CurriculumEngine
    from engines.memory_manager import MemoryManager as MM2
    mm2 = MM2()
    curr = CurriculumEngine(mm2)
    s2 = mm2.get_or_create_student("Verify_Curr_Student")
    unlocked = curr.get_unlocked_topics(s2.id)
    next_t = curr.get_next_topic(s2.id)
    mastery_map = curr.get_mastery_map(s2.id)
    check("get_unlocked_topics()", "variables" in unlocked, f"unlocked includes variables")
    check("get_next_topic()", next_t == "variables", f"next={next_t}")
    check("get_mastery_map()", len(mastery_map) > 0, f"topics={len(mastery_map)}")
except Exception as e:
    check("curriculum engine", False, str(e))

# -- Check 9: MCP tool executor
print("\n[9] MCP tool executor")
try:
    from engines.sandbox import execute_code as sandbox_exec
    from engines.code_analysis import analyze as analyze_fn
    from engines.teaching_engine import TeachingEngine
    from engines.curriculum_engine import CurriculumEngine as CE
    from engines.memory_manager import MemoryManager as MM3
    from llm.ollama_adapter import OllamaAdapter
    from mcp.tools import MCPToolExecutor

    mm3 = MM3()
    llm = OllamaAdapter()
    teaching = TeachingEngine(llm)
    curr3 = CE(mm3)
    executor = MCPToolExecutor(
        memory_manager=mm3,
        curriculum_engine=curr3,
        sandbox_execute=sandbox_exec,
        analyze_code=analyze_fn,
        teaching_engine=teaching,
    )

    r = executor.execute("execute_python_code", {"code": "print(42)"})
    check("MCP execute_python_code", r.get("stdout") == "42", f"stdout={r.get('stdout')!r}")

    r2 = executor.execute("analyze_code", {"code": "x = 1\nprint(x)\n"})
    check("MCP analyze_code", r2.get("success") is True, f"is_valid={r2.get('is_valid_syntax')}")

    r3 = executor.execute("unknown_tool", {})
    check("MCP unknown tool -> error", "error" in r3)
except Exception as e:
    check("MCP executor", False, str(e))

# -- Summary
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"  RESULT: {PASS}/{total} checks passed")
if FAIL == 0:
    print("  ALL CHECKS PASSED -- Skython AI is ready!")
else:
    print(f"  {FAIL} checks FAILED -- see above for details.")
print("=" * 60 + "\n")

sys.exit(0 if FAIL == 0 else 1)
