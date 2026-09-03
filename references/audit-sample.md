# 审计报告样例（真实输出，双向对照）

本文件是 `python scripts/library.py audit` 的**真实运行输出**，未经手工美化。
两个样例对照看：样例 A 是**有问题的库**（结论 ATTENTION），样例 B 是**修复后的库**（结论 PASS）。

配套命令：`guard` 只给通过/不通过（返回码 0/1，适合 CI 卡口），`audit` 给完整可读报告（适合复盘和交给人看）。

---

## 样例 A — 存在未闭环条目（ATTENTION）

复现步骤：`add` 两条 → 只把 `sl_001` 走完闭环，`sl_002` 只记了分没做 `optimize`。

```bash
python scripts/library.py --store /tmp/demo.json audit
```

输出：

```markdown
# skill-library 审计报告

- 生成时间：2026-09-01T21:53:03+08:00
- 库文件：`\tmp\sl_demo.json`

## 1. 总览

| 指标 | 值 | 判读 |
|------|-----|------|
| 条目数 | 2 | 正常 |
| 步数用量 | 0/50 | 健康 |
| 闭环率 | 1/2 | ⚠️ 存在 OPEN |
| 平均分 | 0.70 | 越高越稳 |
| 累计接受改动 | 1 | 棘轮生效次数 |

## 2. 条目明细

| id | task_type | baseline | last | 闭环 | 缺失阶段 |
|----|-----------|----------|------|------|----------|
| sl_001 | competitive_report | 0.85 | 0.85 | ✅ CLOSED | — |
| sl_002 | bess_research | 0.5 | 0.55 | ⚠️ OPEN | optimized |

## 3. 风险与处置

1. `sl_002` 未闭环（缺 optimized）→ 用 `record --id <id> --score <分>` 记分后，`optimize --id <id> --patch '{"approach":"..."}' --score <更高分>` 提改动

## 4. 结论

**ATTENTION** — 存在上述风险项，按处置建议逐条修复后重跑 `guard`。
```

同一状态下 `guard` 的输出（返回码 **1**，卡住流程）：

```
GUARD 步数: 4/50（剩余 46）
GUARD 闭环: 1/2（50%）
OPEN sl_002 [bess_research] 缺阶段: optimized
     兜底动作 → 用 `record --id <id> --score <分>` 记分后，`optimize --id <id> --patch '{"approach":"..."}' --score <更高分>` 提改动
GUARD FAILED: 1 条未闭环，任务不得宣布完成
```

### 怎么处置

按报告第 3 节的指引，对 `sl_002` 补齐 `optimized` 阶段：

```bash
python scripts/library.py --store /tmp/demo.json optimize --id sl_002 \
  --patch '{"approach":"按政策/成本/竞争/技术路线四层拆解","tags":["research","bess"]}' --score 0.72
# → ACCEPTED sl_002: baseline 0.5 -> 0.72 (棘轮提升)
```

注意 `0.72 > 0.5` 才会被接受。如果这次改动实际效果没变好，**不要凑分**——放弃改动、让条目保持 OPEN 是正确结果，硬凑分等于把退化写进库。

---

## 样例 B — 修复后全闭环（PASS）

```markdown
# skill-library 审计报告

- 生成时间：2026-09-01T21:53:29+08:00
- 库文件：`\tmp\sl_demo.json`

## 1. 总览

| 指标 | 值 | 判读 |
|------|-----|------|
| 条目数 | 2 | 正常 |
| 步数用量 | 1/50 | 健康 |
| 闭环率 | 2/2 | ✅ 全闭环 |
| 平均分 | 0.78 | 越高越稳 |
| 累计接受改动 | 2 | 棘轮生效次数 |

## 2. 条目明细

| id | task_type | baseline | last | 闭环 | 缺失阶段 |
|----|-----------|----------|------|------|----------|
| sl_001 | competitive_report | 0.85 | 0.85 | ✅ CLOSED | — |
| sl_002 | bess_research | 0.72 | 0.72 | ✅ CLOSED | — |

## 3. 风险与处置

_无风险项。库处于健康状态。_

## 4. 结论

**PASS** — 库健康，可继续使用。
```

对应 `guard` 输出（返回码 **0**，流程放行）：

```
GUARD 步数: 1/50（剩余 49）
GUARD 闭环: 2/2（100%）
GUARD PASSED: 全部条目已闭环
```

对照 A → B 的变化：闭环率 `1/2 → 2/2`、平均分 `0.70 → 0.78`、接受改动 `1 → 2`、结论 `ATTENTION → PASS`。

---

## 字段怎么读

| 字段 | 含义 | 异常信号与处置 |
|------|------|----------------|
| 条目数 | 库里技能条目总数 | `0` → 空库，先 `add` 沉淀 |
| 步数用量 | 累计写操作数 / 硬上限 | 剩余 ≤5 标 ⚠️ → `reset-steps` 清零或提高 `--max-steps` |
| 闭环率 | CLOSED 条目 / 总条目 | 非 100% → 看第 2 节定位哪条 OPEN |
| 平均分 | 所有条目 `last_score` 均值 | 持续走低 → 复用效果下滑，检查 `approach` 是否过时 |
| 累计接受改动 | 所有条目 `edits` 总数 | 长期为 0 → 棘轮没在用，只沉淀不优化 |
| baseline / last | 棘轮基线 / 最近使用分 | `last < baseline` → 报告会单独列风险项 |
| 缺失阶段 | 未完成的生命周期阶段 | `reused` 缺 → `get`/`find` 一次；`optimized` 缺 → `record` + `optimize` |

## 报告会自动列出的风险项

`audit` 第 3 节除未闭环外，还会自动检出：

| 风险 | 触发条件 | 报告给出的处置 |
|------|----------|----------------|
| 步数接近上限 | 剩余 ≤5 步 | 复核必要性 / `reset-steps` / 提高 `--max-steps` |
| 条目无标签 | `tags` 为空 | 补 `--tags`，否则 `find` 只能靠字符重叠 |
| 使用分低于基线 | `last_score < baseline_score` | 复用效果下滑，检查是否需要改 `approach` |

## 接进流程的两种用法

**Agent 收尾自检**（推荐，硬闭环）：宣布任务完成前跑 `guard`，返回非 0 就不许说"已完成"。

**CI / 定期体检**：

```bash
python scripts/library.py audit > audit-$(date +%F).md   # 存档可读报告
python scripts/library.py guard || exit 1                 # 卡口：不闭环就失败
```

字段结构定义见 `schema.md`，命令总表与 FAQ 见上层 `SKILL.md`。
