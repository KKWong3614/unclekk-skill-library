#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill-library 自测：覆盖沉淀 / 查库 / 棘轮自优化全链路。"""
import subprocess
import sys
import tempfile
from pathlib import Path

PY = sys.executable
LIB = Path(__file__).parent / "library.py"
TMP = Path(tempfile.mkdtemp()) / "test_skill_library.json"

FAILED = False


def run(*a):
    r = subprocess.run([PY, str(LIB), "--store", str(TMP), *a],
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

print("\nALL PASSED" if not FAILED else "\nSOME FAILED")
sys.exit(1 if FAILED else 0)
