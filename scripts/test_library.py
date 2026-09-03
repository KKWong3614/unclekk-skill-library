#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill-library 自测：覆盖沉淀 / 查库 / 棘轮自优化 / 步数限制 / 闭环守卫全链路。"""
import subprocess
import sys
import tempfile
from pathlib import Path

PY = sys.executable
LIB = Path(__file__).parent / "library.py"
TMPDIR = Path(tempfile.mkdtemp())
TMP = TMPDIR / "test_skill_library.json"

FAILED = False


def run(*a):
    r = subprocess.run([PY, str(LIB), "--store", str(TMP), *a],
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def run_at(store, *a):
    """在指定库上运行（用于步数 / 闭环等需要隔离计数的用例）。"""
    r = subprocess.run([PY, str(LIB), "--store", str(store), *a],
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def check(name, cond, extra=""):
    global FAILED
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond:
        FAILED = True


# 1. 沉淀：新增竞品报告技能条目
rc, out, err = run("add", "--task-type", "competitive_report",
                   "--description", "做竞品分析报告",
                   "--approach", "按 Roadmap 拆解：市场定位/功能对比/定价",
                   "--dimensions", "市场定位,功能对比,定价策略",
                   "--tags", "report,competitor", "--score", "0.60")
check("add 返回 ADDED", "ADDED" in out, out)

# 2. 查库：用关键词命中
rc, out, err = run("find", "--query", "竞品报告")
check("find 命中 sl_001", "sl_001" in out, out)

# 3. 记录一次更好的使用结果
rc, out, err = run("record", "--id", "sl_001", "--score", "0.75")
check("record 成功", "RECORDED" in out, out)

# 4. 自优化：提出改进并被接受（棘轮提升）
rc, out, err = run("optimize", "--id", "sl_001",
                   "--patch", '{"approach":"按 Roadmap 拆解：市场定位/功能对比/定价/渠道"}',
                   "--score", "0.85")
check("optimize 提升被接受", "ACCEPTED" in out, out)

# 5. 自优化：未提升必须被拒绝（棘轮守住）
rc, out, err = run("optimize", "--id", "sl_001",
                   "--patch", '{"approach":"退化版本"}', "--score", "0.80")
check("optimize 不提升被拒绝", "REJECTED" in out, out)

# 6. 内容未被回滚破坏：approach 仍是提升后的版本
rc, out, err = run("get", "--id", "sl_001")
check("内容未被退化版覆盖", "渠道" in out and "退化" not in out, out)

# 7. list 正常
rc, out, err = run("list")
check("list 有条目", "sl_001" in out, out)

# 8. stats 正常
rc, out, err = run("stats")
check("stats 输出条目数", "条目数" in out, out)

# 9. score 越界应被拒绝（rc != 0）
rc, out, err = run("record", "--id", "sl_001", "--score", "1.5")
check("score 越界被拒(rc!=0)", rc != 0, f"rc={rc} err={err}")

# 10. 空 approach 添加应被拒（rc != 0）
rc, out, err = run("add", "--task-type", "bad", "--description", "d",
                   "--approach", "", "--score", "0.5")
check("空 approach 被拒(rc!=0)", rc != 0, f"rc={rc} err={err}")

# 11. optimize 坏 patch JSON 应返回非 0
rc, out, err = run("optimize", "--id", "sl_001", "--patch", "{bad-json", "--score", "0.90")
check("坏 patch JSON 返回非0", rc != 0, f"rc={rc} err={err}")

# 12. get 不存在的 id 应返回非 0
rc, out, err = run("get", "--id", "sl_999")
check("get 不存在返回非0", rc != 0, f"rc={rc} err={err}")

# 13. record 不存在的 id 应返回非 0
rc, out, err = run("record", "--id", "sl_999", "--score", "0.9")
check("record 不存在返回非0", rc != 0, f"rc={rc} err={err}")

# 14. add 成功时退出码必须为 0（回归：cmd_add 返回 id 曾被当作退出码）
rc, out, err = run("add", "--task-type", "extra_case", "--description", "附加条目",
                   "--approach", "拆解：A→B", "--tags", "extra", "--score", "0.4")
check("add 成功退出码为0", rc == 0 and "ADDED" in out, f"rc={rc} out={out} err={err}")

# 15. list 输出闭环标记（CLOSED / OPEN）
rc, out, err = run("list")
check("list 显示闭环标记", ("CLOSED" in out or "OPEN" in out), out)

# 16. stats 输出闭环率与步数用量
rc, out, err = run("stats")
check("stats 含闭环率与步数", "闭环率" in out and "步数用量" in out, out)

# 17. patch 传非 JSON 对象（数组）应被拒
rc, out, err = run("optimize", "--id", "sl_001", "--patch", '["approach"]', "--score", "0.95")
check("patch 非对象被拒(rc!=0)", rc != 0, f"rc={rc} err={err}")

# 18. 白名单：patch 含结构字段 id 应被拒
rc, out, err = run("optimize", "--id", "sl_001",
                   "--patch", '{"id":"hacked","approach":"x"}', "--score", "0.95")
check("patch 含 id 被白名单拒绝", rc != 0 and "REJECTED" in out, f"rc={rc} out={out}")

# ---- 以下用独立库，避免与上面的步数计数互相干扰 ----

# 19. 只 add 不复用 → guard 必须检出 OPEN 并返回非 0
G = TMPDIR / "guard_case.json"
run_at(G, "add", "--task-type", "loop_case", "--description", "闭环用例",
       "--approach", "拆解：X→Y", "--tags", "loop", "--score", "0.5")
rc, out, err = run_at(G, "guard")
check("未闭环 guard 返回非0", rc != 0 and "OPEN" in out, f"rc={rc} out={out}")

# 20. 走完闭环（get 打 reused 戳 + optimize 打 optimized 戳）→ guard 通过
run_at(G, "get", "--id", "sl_001")
run_at(G, "optimize", "--id", "sl_001", "--patch", '{"approach":"拆解：X→Y→Z"}', "--score", "0.7")
rc, out, err = run_at(G, "guard")
check("闭环后 guard 通过(rc=0)", rc == 0 and "GUARD PASSED" in out, f"rc={rc} out={out}")

# 21. audit 报告含关键字段与结论
rc, out, err = run_at(G, "audit")
check("audit 含总览/闭环率/结论",
      "审计报告" in out and "闭环率" in out and ("PASS" in out or "ATTENTION" in out), out[:200])

# 22. 步数超限必须硬中止，退出码为 2
S = TMPDIR / "step_case.json"
rc, out, err = run_at(S, "--max-steps", "1", "add", "--task-type", "s1",
                      "--description", "d1", "--approach", "拆解：A", "--score", "0.5")
check("首次 add 在上限内成功", rc == 0, f"rc={rc} out={out}")
rc, out, err = run_at(S, "--max-steps", "1", "add", "--task-type", "s2",
                      "--description", "d2", "--approach", "拆解：B", "--score", "0.5")
check("步数超限硬中止(rc=2)", rc == 2 and "STOP" in err, f"rc={rc} err={err}")

# 23. 只读命令不受步数限制影响（仍可 list / audit 排查）
rc, out, err = run_at(S, "--max-steps", "1", "list")
check("超限后只读命令仍可用", rc == 0 and "sl_001" in out, f"rc={rc} out={out}")

# 24. reset-steps 兜底出口：清零后可继续写
rc, out, err = run_at(S, "reset-steps")
check("reset-steps 清零", rc == 0 and "RESET" in out, f"rc={rc} out={out}")
rc, out, err = run_at(S, "--max-steps", "1", "add", "--task-type", "s3",
                      "--description", "d3", "--approach", "拆解：C", "--score", "0.5")
check("清零后可继续写入", rc == 0 and "ADDED" in out, f"rc={rc} out={out}")

# 25. --max-steps 非法值应报错退出
rc, out, err = run_at(S, "--max-steps", "0", "list")
check("--max-steps<1 被拒(rc!=0)", rc != 0, f"rc={rc} err={err}")

print("\nALL PASSED" if not FAILED else "\nSOME FAILED")
sys.exit(1 if FAILED else 0)
