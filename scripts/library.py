#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-library — Voyager 式技能库 + SkillOpt 式自优化编排器（零第三方依赖）

核心能力（对应论文）：
  1. 沉淀 capture  ：把成功任务的拆解方式 / 关键维度存成可复用技能条目
  2. 复用 retrieve  ：新任务先查库，复用已有 Roadmap，只在缺口补新能力
  3. 自优化 optimize ：用独立验证分评估效果；只有严格提升才接受改动（棘轮，只留改进）

硬代码保障（不是声明式约定，全部在本文件内强制执行）：
  - 步数限制：写操作（add/record/optimize）累计计步并持久化，超过 --max-steps 硬中止（exit 2）
  - 严格闭环：条目生命周期 captured → reused → optimized，未走完即 OPEN，guard 检出则 exit 1
  - 兜底保障：每种中止都打印可执行的下一步动作，绝不裸抛堆栈
  - 白名单：optimize 补丁只能改 6 个业务字段，触碰结构字段直接 REJECTED

存储：单个 JSON 文件，默认 ~/.workbuddy/skill_library.json，可用 --store 覆盖。
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_STORE = Path.home() / ".workbuddy" / "skill_library.json"

# 硬代码：写操作累计步数上限（防失控循环 / 防 Agent 无限自优化）
DEFAULT_MAX_STEPS = 50
# 硬代码：计入步数的命令（只读命令不计步）
STEP_COMMANDS = {"add", "record", "optimize"}
# 硬代码：闭环三阶段，缺一即 OPEN
LIFECYCLE_STAGES = ("captured", "reused", "optimized")
# 硬代码：optimize 补丁字段白名单
ALLOWED_PATCH_KEYS = {
    "approach", "description", "task_type", "tags", "key_dimensions", "usage_notes",
}
# 退出码约定：0 正常 / 1 业务失败（NOT FOUND、未闭环、非法输入） / 2 步数超限硬中止
EXIT_OK, EXIT_FAIL, EXIT_STEP_LIMIT = 0, 1, 2


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_store(path: Path):
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "entries" in data:
                data.setdefault("meta", {})
                data["meta"].setdefault("steps", 0)
                return data
        except Exception as exc:
            print(
                f"WARNING: 库文件损坏 ({path})，解析失败：{exc!r}。已新建空库，原数据本次会话不可见。\n"
                f"        恢复建议：\n"
                f"         1. 检查同目录下 {path.name}.tmp 临时文件是否完好，可改名为 {path.name} 恢复；\n"
                f"         2. 回想最近是否有并发写入或异常中断导致截断；\n"
                f"         3. 如有历史备份，请用备份覆盖 {path}。",
                file=sys.stderr,
            )
    return {"entries": {}, "meta": {"created": now_iso(), "version": 1, "steps": 0}}


def save_store(path: Path, data):
    # 原子写：先写临时文件再 rename，避免半截写入损坏库
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / (path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        # 友好化：把权限/磁盘满等技术错误翻译成可执行的排查步骤，而不是抛堆栈
        print(
            f"ERROR: 无法写入库文件 ({path})：{exc}\n"
            f"       排查建议：\n"
            f"         1. 检查目标目录是否有写入权限；\n"
            f"         2. 检查磁盘是否已满（可用 df -h / 资源管理器确认）；\n"
            f"         3. 用 --store <其他可写路径> 指定一个可写位置后重试。",
            file=sys.stderr,
        )
        sys.exit(EXIT_FAIL)


def new_id(data):
    n = len(data["entries"]) + 1
    return f"sl_{n:03d}"


# ---------------------------------------------------------------- 硬代码：步数限制

def enforce_step_limit(data, max_steps: int, cmd: str):
    """硬代码步数闸门：写操作执行前检查累计步数，超限直接中止（exit 2）。

    这不是建议，是强制：Agent 无法通过 prompt 绕过。
    """
    used = int(data.get("meta", {}).get("steps", 0))
    if used >= max_steps:
        print(
            f"STOP: 步数已达上限 {used}/{max_steps}，拒绝执行写操作 `{cmd}`（硬代码保障，防失控循环）。\n"
            f"      兜底动作，三选一：\n"
            f"        1. 先用 `audit` 看清库现状，确认这些写操作是否真的必要；\n"
            f"        2. 确认本轮任务已完成，用 `reset-steps` 清零计数后继续；\n"
            f"        3. 明确需要更多步数，用 `--max-steps {max_steps * 2}` 提高上限。",
            file=sys.stderr,
        )
        sys.exit(EXIT_STEP_LIMIT)


def bump_step(data, max_steps: int):
    """写操作成功后累计步数，并在接近上限时提前预警（兜底：不等撞墙才说）。"""
    meta = data.setdefault("meta", {})
    meta["steps"] = int(meta.get("steps", 0)) + 1
    used = meta["steps"]
    if max_steps - used <= 5 and used < max_steps:
        print(f"WARNING: 步数 {used}/{max_steps}，剩余 {max_steps - used} 步即触发硬中止。"
              f"建议先 `audit` 复核，或 `reset-steps` 清零。", file=sys.stderr)


# ------------------------------------------------------------ 硬代码：闭环状态机

def _lifecycle(entry) -> dict:
    """读取条目生命周期，兼容 v1.2.x 老库（无 lifecycle 字段时按 created 推断 captured）。"""
    lc = entry.get("lifecycle")
    if not isinstance(lc, dict):
        lc = {"captured": entry.get("created") or now_iso(), "reused": None, "optimized": None}
        # 老库若已有 edits，说明历史上被接受过改动，视为已 optimized
        if entry.get("edits"):
            lc["reused"] = lc["reused"] or entry["edits"][0].get("at")
            lc["optimized"] = entry["edits"][-1].get("at")
        entry["lifecycle"] = lc
    for stage in LIFECYCLE_STAGES:
        lc.setdefault(stage, None)
    return lc


def mark_stage(entry, stage: str):
    """打生命周期戳（幂等：已打过不覆盖首次时间）。"""
    lc = _lifecycle(entry)
    if stage in LIFECYCLE_STAGES and not lc.get(stage):
        lc[stage] = now_iso()


def missing_stages(entry):
    lc = _lifecycle(entry)
    return [s for s in LIFECYCLE_STAGES if not lc.get(s)]


def is_closed(entry) -> bool:
    return not missing_stages(entry)


# 兜底动作：每个缺失阶段对应一条可直接执行的命令
STAGE_FIX = {
    "captured": "用 `add` 重新沉淀该条目（异常情况，通常不会缺）",
    "reused": "用 `get --id <id>` 或 `find --query <关键词>` 复用一次（会自动打 reused 戳）",
    "optimized": "用 `record --id <id> --score <分>` 记分后，`optimize --id <id> --patch '{\"approach\":\"...\"}' --score <更高分>` 提改动",
}


# ---------------------------------------------------------------------- 业务命令

def _parse_score(raw) -> float:
    """解析 --score，非法输入或越界给出明确错误并退出。

    score 是 0-1 之间的验证分比例（用户评分 / LLM 自评 / 任务成功率）。
    """
    try:
        v = float(raw)
    except (TypeError, ValueError):
        print(f"ERROR: --score 必须是数字，收到: {raw!r}", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    if not (0.0 <= v <= 1.0):
        print(f"ERROR: --score 必须在 0-1 之间（代表验证分比例），收到: {v}。"
              f"请填写 0-1 的数字，如 0.75。", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    return v


def _split(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _score_match(entry, query, tags):
    text = " ".join([
        entry.get("description", ""),
        entry.get("approach", ""),
        entry.get("task_type", ""),
    ])
    s = 0.0
    # 标签匹配权重高
    if tags:
        et = set(entry.get("tags", []))
        s += 2.0 * len(set(tags) & et)
    # 文本：字符级重叠（兼容中文，无空格分词）
    # 例：查询「竞品报告」不是「做竞品分析报告」的连续子串，但字都出现过 → 命中
    q = (query or "").strip()
    if q:
        chars = {c for c in q if not c.isspace()}
        if chars:
            present = sum(1 for c in chars if c in text)
            s += present / len(chars) * 3.0  # 覆盖率打分
    return s


def cmd_add(args, data, path):
    # 输入护栏：核心字段非空，且 approach 必须可执行（避免下游 get 拿到不可复用产出）
    if not (args.task_type or "").strip():
        print("ERROR: --task-type 不能为空，请填写任务类型键（如 competitive_report）。", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    if not (args.description or "").strip():
        print("ERROR: --description 不能为空，请填写这条技能解决什么任务。", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    if not (args.approach or "").strip():
        print("ERROR: --approach 不能为空，且必须可执行（写具体步骤，如『按 Roadmap 拆解：A→B→C』），"
              "不能是『研究一下』这类模糊词——它是下游复用的核心输入。", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    entry = {
        "id": new_id(data),
        "task_type": args.task_type,
        "description": args.description,
        "approach": args.approach,
        "key_dimensions": _split(args.dimensions),
        "tags": _split(args.tags),
        "baseline_score": _parse_score(args.score),
        "last_score": _parse_score(args.score),
        "edits": [],
        "lifecycle": {"captured": now_iso(), "reused": None, "optimized": None},
        "created": now_iso(),
        "updated": now_iso(),
    }
    data["entries"][entry["id"]] = entry
    bump_step(data, args.max_steps)
    save_store(path, data)
    print(f"ADDED {entry['id']} (task_type={args.task_type}, baseline={args.score})")
    return entry["id"]


def cmd_find(args, data, path):
    tags = _split(args.tags)
    # 一次性算分后排序，避免重复计算与不稳定排序
    scored = {e["id"]: (s, e) for e in data["entries"].values()
              if (s := _score_match(e, args.query, tags)) > 0}
    if not scored:
        print("NO MATCH（库中无相关条目，请回退到 add 从零沉淀，不要硬用不相关条目）")
        return
    hits = sorted(scored.items(), key=lambda kv: kv[1][0], reverse=True)[: args.top]
    for _id, (s, e) in hits:
        mark_stage(e, "reused")  # 命中即视为复用，推进闭环（只读命令，不计步）
        print(f"#{e['id']} [{e['task_type']}] score={e['last_score']} tags={e['tags']}")
        print(f"   {e['description']}")
    save_store(path, data)


def cmd_get(args, data, path):
    e = data["entries"].get(args.id)
    if not e:
        print(f"NOT FOUND: {args.id}（用 list 查看全部 id，或 find 按关键词检索）", file=sys.stderr)
        return EXIT_FAIL
    mark_stage(e, "reused")  # 取出即视为复用，推进闭环（只读命令，不计步）
    save_store(path, data)
    print(json.dumps(e, ensure_ascii=False, indent=2))


def cmd_list(args, data, path):
    if not data["entries"]:
        print("EMPTY LIBRARY")
        return
    for e in data["entries"].values():
        flag = "CLOSED" if is_closed(e) else "OPEN"
        print(f"{e['id']}  {e['task_type']:<22} score={e['last_score']:<5} "
              f"dims={len(e['key_dimensions'])} tags={e['tags']} {flag}")


def cmd_record(args, data, path):
    e = data["entries"].get(args.id)
    if not e:
        print(f"NOT FOUND: {args.id}（用 list 查看全部 id，或 find 按关键词检索）", file=sys.stderr)
        return EXIT_FAIL
    e["last_score"] = _parse_score(args.score)
    e["updated"] = now_iso()
    mark_stage(e, "reused")  # 记分前提是用过，推进闭环
    if args.note:
        e.setdefault("usage_notes", []).append(
            {"at": now_iso(), "note": args.note, "score": float(args.score)}
        )
    bump_step(data, args.max_steps)
    save_store(path, data)
    print(f"RECORDED {args.id} -> last_score={args.score}")


def cmd_optimize(args, data, path):
    """SkillOpt 式棘轮：只有新分严格高于基线，才接受对技能的改动。"""
    e = data["entries"].get(args.id)
    if not e:
        print(f"NOT FOUND: {args.id}（用 list 查看全部 id，或 find 按关键词检索）", file=sys.stderr)
        return EXIT_FAIL
    try:
        patch = json.loads(args.patch)
    except Exception as ex:
        print(f"ERROR: --patch 不是合法 JSON：{ex}。\n"
              f"       示例：--patch '{{\"approach\":\"按 Roadmap 拆解：市场定位/功能对比/定价/渠道\"}}'",
              file=sys.stderr)
        return EXIT_FAIL
    if not isinstance(patch, dict):
        print(f"ERROR: --patch 必须是 JSON 对象（{{\"字段\":\"值\"}}），收到 {type(patch).__name__}。",
              file=sys.stderr)
        return EXIT_FAIL
    # 白名单防护 — 含非法字段时直接拒绝，而非静默丢弃
    disallowed = set(patch.keys()) - ALLOWED_PATCH_KEYS
    if disallowed:
        print(f"REJECTED {args.id}: 拒绝非法字段 {sorted(disallowed)}"
              f"（只允许白名单字段 {sorted(ALLOWED_PATCH_KEYS)}）")
        return EXIT_FAIL

    new_score = _parse_score(args.score)
    baseline = _parse_score(e["baseline_score"])
    if new_score > baseline:
        for k, v in patch.items():
            e[k] = v
        e["baseline_score"] = new_score
        e["last_score"] = new_score
        e["updated"] = now_iso()
        e.setdefault("edits", []).append({"at": now_iso(), "patch": patch, "score": new_score})
        mark_stage(e, "reused")
        mark_stage(e, "optimized")  # 棘轮接受 → 闭环完成
        bump_step(data, args.max_steps)
        save_store(path, data)
        print(f"ACCEPTED {args.id}: baseline {baseline} -> {new_score} (棘轮提升)")
    else:
        bump_step(data, args.max_steps)  # 被拒也算一次尝试，防无限重试
        save_store(path, data)
        print(f"REJECTED {args.id}: 新分 {new_score} 未严格高于基线 {baseline}，"
              f"改动已回滚（只留改进）")


def cmd_stats(args, data, path):
    n = len(data["entries"])
    if n == 0:
        print("EMPTY LIBRARY")
        return
    scores = [e["last_score"] for e in data["entries"].values()]
    closed = sum(1 for e in data["entries"].values() if is_closed(e))
    print(f"条目数: {n}")
    print(f"平均分: {sum(scores) / n:.2f}")
    print(f"最高分: {max(scores):.2f}  最低分: {min(scores):.2f}")
    print(f"闭环率: {closed}/{n} ({closed / n * 100:.0f}%)")
    print(f"步数用量: {data.get('meta', {}).get('steps', 0)}/{args.max_steps}")


def cmd_guard(args, data, path):
    """硬代码闭环守卫：检出未闭环条目与步数风险，有问题返回非 0。

    用于 CI / Agent 收尾自检——不通过就不允许宣布任务完成。
    """
    n = len(data["entries"])
    used = int(data.get("meta", {}).get("steps", 0))
    print(f"GUARD 步数: {used}/{args.max_steps}（剩余 {max(args.max_steps - used, 0)}）")
    if n == 0:
        print("GUARD PASSED: 空库，无未闭环条目")
        return
    open_entries = [e for e in data["entries"].values() if not is_closed(e)]
    closed = n - len(open_entries)
    print(f"GUARD 闭环: {closed}/{n}（{closed / n * 100:.0f}%）")
    for e in open_entries:
        miss = missing_stages(e)
        print(f"OPEN {e['id']} [{e['task_type']}] 缺阶段: {', '.join(miss)}")
        for stage in miss:
            print(f"     兜底动作 → {STAGE_FIX[stage]}")
    save_store(path, data)  # 回写 lifecycle 兼容字段（老库首次 guard 会补全）
    if open_entries:
        print(f"GUARD FAILED: {len(open_entries)} 条未闭环，任务不得宣布完成", file=sys.stderr)
        return EXIT_FAIL
    print("GUARD PASSED: 全部条目已闭环")


def cmd_audit(args, data, path):
    """输出 Markdown 审计报告（样例见 references/audit-sample.md）。"""
    n = len(data["entries"])
    used = int(data.get("meta", {}).get("steps", 0))
    entries = list(data["entries"].values())
    closed = [e for e in entries if is_closed(e)]
    open_e = [e for e in entries if not is_closed(e)]
    scores = [e["last_score"] for e in entries] or [0.0]
    accepted = sum(len(e.get("edits", [])) for e in entries)

    print("# skill-library 审计报告")
    print()
    print(f"- 生成时间：{now_iso()}")
    print(f"- 库文件：`{path}`")
    print()
    print("## 1. 总览")
    print()
    print("| 指标 | 值 | 判读 |")
    print("|------|-----|------|")
    print(f"| 条目数 | {n} | {'空库，先 add 沉淀' if n == 0 else '正常'} |")
    print(f"| 步数用量 | {used}/{args.max_steps} | "
          f"{'⚠️ 接近上限' if args.max_steps - used <= 5 else '健康'} |")
    print(f"| 闭环率 | {len(closed)}/{n} | {'✅ 全闭环' if n and not open_e else '⚠️ 存在 OPEN'} |")
    print(f"| 平均分 | {sum(scores) / len(scores):.2f} | 越高越稳 |")
    print(f"| 累计接受改动 | {accepted} | 棘轮生效次数 |")
    print()
    print("## 2. 条目明细")
    print()
    if n == 0:
        print("_空库，无条目。_")
    else:
        print("| id | task_type | baseline | last | 闭环 | 缺失阶段 |")
        print("|----|-----------|----------|------|------|----------|")
        for e in entries:
            miss = missing_stages(e)
            print(f"| {e['id']} | {e['task_type']} | {e['baseline_score']} | {e['last_score']} | "
                  f"{'✅ CLOSED' if not miss else '⚠️ OPEN'} | {', '.join(miss) or '—'} |")
    print()
    print("## 3. 风险与处置")
    print()
    risks = []
    if args.max_steps - used <= 5:
        risks.append(f"步数 {used}/{args.max_steps} 接近硬上限 → 先复核必要性，"
                     f"或 `reset-steps` 清零，或提高 `--max-steps`")
    for e in open_e:
        risks.append(f"`{e['id']}` 未闭环（缺 {', '.join(missing_stages(e))}）→ "
                     f"{STAGE_FIX[missing_stages(e)[0]]}")
    for e in entries:
        if not e.get("tags"):
            risks.append(f"`{e['id']}` 无标签 → 后续 find 只能靠字符重叠，建议补 `--tags`")
        if e["last_score"] < e["baseline_score"]:
            risks.append(f"`{e['id']}` last_score({e['last_score']}) 低于 baseline({e['baseline_score']})"
                         f" → 复用效果下滑，检查是否需要改 approach")
    if risks:
        for i, r in enumerate(risks, 1):
            print(f"{i}. {r}")
    else:
        print("_无风险项。库处于健康状态。_")
    print()
    print("## 4. 结论")
    print()
    verdict = "PASS" if (n and not open_e and args.max_steps - used > 5) else "ATTENTION"
    print(f"**{verdict}** — " + ("库健康，可继续使用。" if verdict == "PASS"
                                 else "存在上述风险项，按处置建议逐条修复后重跑 `guard`。"))


def cmd_reset_steps(args, data, path):
    """兜底出口：确认本轮任务完成后，清零步数计数继续下一轮。"""
    old = int(data.get("meta", {}).get("steps", 0))
    data.setdefault("meta", {})["steps"] = 0
    save_store(path, data)
    print(f"RESET 步数: {old} -> 0（上限 {args.max_steps}）")


def main():
    p = argparse.ArgumentParser(description="skill-library: Voyager 技能库 + SkillOpt 自优化")
    p.add_argument("--store", default=str(DEFAULT_STORE),
                   help="库文件路径（默认 ~/.workbuddy/skill_library.json）")
    p.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS,
                   help=f"写操作累计步数硬上限，超限中止（默认 {DEFAULT_MAX_STEPS}）")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="新增技能条目")
    a.add_argument("--task-type", required=True)
    a.add_argument("--description", required=True)
    a.add_argument("--approach", required=True, help="可复用的拆解方式 / Roadmap")
    a.add_argument("--dimensions", default="", help="关键维度，逗号分隔")
    a.add_argument("--tags", default="", help="标签，逗号分隔")
    a.add_argument("--score", default="0.0", help="基线验证分（0-1）")
    a.set_defaults(func=cmd_add)

    f = sub.add_parser("find", help="按关键词/标签查库")
    f.add_argument("--query", default="")
    f.add_argument("--tags", default="")
    f.add_argument("--top", type=int, default=3)
    f.set_defaults(func=cmd_find)

    g = sub.add_parser("get", help="查看单条")
    g.add_argument("--id", required=True)
    g.set_defaults(func=cmd_get)

    l = sub.add_parser("list", help="列出全部（带闭环标记）")
    l.set_defaults(func=cmd_list)

    r = sub.add_parser("record", help="记录一次使用结果分")
    r.add_argument("--id", required=True)
    r.add_argument("--score", required=True)
    r.add_argument("--note", default="")
    r.set_defaults(func=cmd_record)

    o = sub.add_parser("optimize", help="提出对技能的改动，严格提升才接受")
    o.add_argument("--id", required=True)
    o.add_argument("--patch", required=True, help='JSON 补丁，如 {"approach":"..."}')
    o.add_argument("--score", required=True, help="应用该改动后的验证分（0-1）")
    o.set_defaults(func=cmd_optimize)

    st = sub.add_parser("stats", help="库统计（含闭环率与步数用量）")
    st.set_defaults(func=cmd_stats)

    gd = sub.add_parser("guard", help="闭环守卫：有未闭环条目则返回非 0（收尾自检用）")
    gd.set_defaults(func=cmd_guard)

    au = sub.add_parser("audit", help="输出 Markdown 审计报告")
    au.set_defaults(func=cmd_audit)

    rs = sub.add_parser("reset-steps", help="清零步数计数（兜底出口）")
    rs.set_defaults(func=cmd_reset_steps)

    args = p.parse_args()
    if args.max_steps < 1:
        print(f"ERROR: --max-steps 必须 >= 1，收到 {args.max_steps}。", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    path = Path(args.store)
    data = load_store(path)
    # 硬代码闸门：写操作在执行前先过步数检查
    if args.cmd in STEP_COMMANDS:
        enforce_step_limit(data, args.max_steps, args.cmd)
    rc = args.func(args, data, path)
    # 只把 int 当退出码：cmd_add 会返回新条目 id（字符串），不能当错误码退出
    if isinstance(rc, int) and rc != 0:
        sys.exit(rc)


if __name__ == "__main__":
    main()
