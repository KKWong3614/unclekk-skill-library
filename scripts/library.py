#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-library — Voyager 式技能库 + SkillOpt 式自优化编排器（零第三方依赖）

核心能力（对应论文）：
  1. 沉淀 capture  ：把成功任务的拆解方式 / 关键维度存成可复用技能条目
  2. 复用 retrieve  ：新任务先查库，复用已有 Roadmap，只在缺口补新能力
  3. 自优化 optimize ：用独立验证分评估效果；只有严格提升才接受改动（棘轮，只留改进）

存储：单个 JSON 文件，默认 ~/.workbuddy/skill_library.json，可用 --store 覆盖。
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_STORE = Path.home() / ".workbuddy" / "skill_library.json"


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_store(path: Path):
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "entries" in data:
                return data
        except Exception as exc:
            print(f"WARNING: 库文件损坏 ({path})，原有 {exc!r}。已新建空库，原有数据已丢失，请手动备份恢复。", file=sys.stderr)
    return {"entries": {}, "meta": {"created": now_iso(), "version": 1}}


def save_store(path: Path, data):
    # 原子写：先写临时文件再 rename，避免半截写入损坏库
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def new_id(data):
    n = len(data["entries"]) + 1
    return f"sl_{n:03d}"


def _parse_score(raw) -> float:
    """解析 --score，非法输入给出明确错误并退出。"""
    try:
        return float(raw)
    except (TypeError, ValueError):
        print(f"ERROR: --score 必须是数字，收到: {raw!r}", file=sys.stderr)
        sys.exit(1)


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
        "created": now_iso(),
        "updated": now_iso(),
    }
    data["entries"][entry["id"]] = entry
    save_store(path, data)
    print(f"ADDED {entry['id']} (task_type={args.task_type}, baseline={args.score})")
    return entry["id"]


def cmd_find(args, data, path):
    tags = _split(args.tags)
    ranked = [e for e in data["entries"].values() if _score_match(e, args.query, tags) > 0]
    ranked.sort(key=lambda e: _score_match(e, args.query, tags), reverse=True)
    if not ranked:
        print("NO MATCH")
        return
    for e in ranked[: args.top]:
        print(f"#{e['id']} [{e['task_type']}] score={e['last_score']} tags={e['tags']}")
        print(f"   {e['description']}")


def cmd_get(args, data, path):
    e = data["entries"].get(args.id)
    if not e:
        print(f"NOT FOUND: {args.id}")
        return
    print(json.dumps(e, ensure_ascii=False, indent=2))


def cmd_list(args, data, path):
    if not data["entries"]:
        print("EMPTY LIBRARY")
        return
    for e in data["entries"].values():
        print(f"{e['id']}  {e['task_type']:<22} score={e['last_score']:<5} "
              f"dims={len(e['key_dimensions'])} tags={e['tags']}")


def cmd_record(args, data, path):
    e = data["entries"].get(args.id)
    if not e:
        print(f"NOT FOUND: {args.id}")
        return
    e["last_score"] = _parse_score(args.score)
    e["updated"] = now_iso()
    if args.note:
        e.setdefault("usage_notes", []).append(
            {"at": now_iso(), "note": args.note, "score": float(args.score)}
        )
    save_store(path, data)
    print(f"RECORDED {args.id} -> last_score={args.score}")


def cmd_optimize(args, data, path):
    """SkillOpt 式棘轮：只有新分严格高于基线，才接受对技能的改动。"""
    e = data["entries"].get(args.id)
    if not e:
        print(f"NOT FOUND: {args.id}")
        return
    try:
        patch = json.loads(args.patch)
    except Exception as ex:
        print(f"BAD PATCH JSON: {ex}")
        return
    # P0: 白名单防护 — 含非法字段时直接拒绝，而非静默丢弃
    ALLOWED_KEYS = {"approach", "description", "task_type", "tags", "key_dimensions", "usage_notes"}
    patch_keys = set(patch.keys())
    disallowed = patch_keys - ALLOWED_KEYS
    if disallowed:
        print(f"REJECTED {args.id}: 拒绝非法字段 {sorted(disallowed)}（只允许白名单字段）")
        return 1

    new_score = _parse_score(args.score)
    baseline = _parse_score(e["baseline_score"])
    if new_score > baseline:
        # 仅改白名单字段
        for k, v in patch.items():
            e[k] = v
        e["baseline_score"] = new_score
        e["last_score"] = new_score
        e["updated"] = now_iso()
        e.setdefault("edits", []).append({"at": now_iso(), "patch": patch, "score": new_score})
        save_store(path, data)
        print(f"ACCEPTED {args.id}: baseline {baseline} -> {new_score} (棘轮提升)")
    else:
        print(f"REJECTED {args.id}: 新分 {new_score} 未严格高于基线 {baseline}，"
              f"改动已回滚（只留改进）")


def cmd_stats(args, data, path):
    n = len(data["entries"])
    if n == 0:
        print("EMPTY LIBRARY")
        return
    scores = [e["last_score"] for e in data["entries"].values()]
    print(f"条目数: {n}")
    print(f"平均分: {sum(scores) / n:.2f}")
    print(f"最高分: {max(scores):.2f}  最低分: {min(scores):.2f}")


def main():
    p = argparse.ArgumentParser(description="skill-library: Voyager 技能库 + SkillOpt 自优化")
    p.add_argument("--store", default=str(DEFAULT_STORE), help="库文件路径（默认 ~/.workbuddy/skill_library.json）")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="新增技能条目")
    a.add_argument("--task-type", required=True)
    a.add_argument("--description", required=True)
    a.add_argument("--approach", required=True, help="可复用的拆解方式 / Roadmap")
    a.add_argument("--dimensions", default="", help="关键维度，逗号分隔")
    a.add_argument("--tags", default="", help="标签，逗号分隔")
    a.add_argument("--score", default="0.0", help="基线验证分")
    a.set_defaults(func=cmd_add)

    f = sub.add_parser("find", help="按关键词/标签查库")
    f.add_argument("--query", default="")
    f.add_argument("--tags", default="")
    f.add_argument("--top", type=int, default=3)
    f.set_defaults(func=cmd_find)

    g = sub.add_parser("get", help="查看单条")
    g.add_argument("--id", required=True)
    g.set_defaults(func=cmd_get)

    l = sub.add_parser("list", help="列出全部")
    l.set_defaults(func=cmd_list)

    r = sub.add_parser("record", help="记录一次使用结果分")
    r.add_argument("--id", required=True)
    r.add_argument("--score", required=True)
    r.add_argument("--note", default="")
    r.set_defaults(func=cmd_record)

    o = sub.add_parser("optimize", help="提出对技能的改动，严格提升才接受")
    o.add_argument("--id", required=True)
    o.add_argument("--patch", required=True, help='JSON 补丁，如 {"approach":"..."}')
    o.add_argument("--score", required=True, help="应用该改动后的验证分")
    o.set_defaults(func=cmd_optimize)

    st = sub.add_parser("stats", help="库统计")
    st.set_defaults(func=cmd_stats)

    args = p.parse_args()
    path = Path(args.store)
    data = load_store(path)
    rc = args.func(args, data, path)
    if rc is not None:
        sys.exit(rc)


if __name__ == "__main__":
    main()
