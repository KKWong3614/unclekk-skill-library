# skill-library · 让 Agent 把技能攒成库，越用越强

**版本 v1.3.0** ｜ 纯本地 · 零第三方依赖 · 无需 API Key 与网络
**Version v1.3.0** ｜ Fully local · zero third-party deps · no API key or network

> 让 Agent 把技能攒成库，越用越强。
>
> Lets an agent accumulate skills into a library and grow stronger with use.

Voyager 式终身技能库 + SkillOpt 式严格自优化，落地为一个零依赖、可运行的命令行编排器。把成功任务的拆解方式与关键维度沉淀成可复用技能条目，新任务先查库复用、只在缺口补新能力；并用独立验证分做棘轮式自优化（**严格提升才接受改动**）。

A Voyager-style lifelong skill library plus SkillOpt-style strict self-optimization, implemented as a zero-dependency, runnable command-line orchestrator. It distills the decomposition approach and key dimensions of successful tasks into reusable skill entries; new tasks first query the library for reuse and only add new capability at the gaps. Independent validation scores drive ratchet-style self-optimization (**changes are accepted only on strict improvement**).

配套文章：「读论文造技能 之三」—— *这样做，让Agent把技能攒成库，越用越强*
Companion article: "Reading Papers to Build Skills, Part 3" — *Do this to let your agent accumulate skills into a library and grow stronger*.

## 理论来源 Theoretical Basis

| 论文 | 机构 | 贡献 |
|------|------|------|
| **Voyager** | NVIDIA + Caltech | 终身技能库：每次成功都把关键操作写成可复用技能条目，下次先查库复用、只在缺口补新能力。 |
| **SkillOpt** | Microsoft | 技能自优化：用独立验证分评估；只有严格提升时才接受对技能的修改——只留改进，不留退化。 |

| Paper | Institution | Contribution |
|-------|-------------|--------------|
| **Voyager** | NVIDIA + Caltech | Lifelong skill library: every success writes key operations as reusable skill entries; next time, query the library for reuse and only add new capability at the gaps. |
| **SkillOpt** | Microsoft | Skill self-optimization: evaluate with an independent validation score; accept modifications to the skill only on strict improvement — keep the gains, drop the regressions. |

本技能是这两篇论文思想的**工程落地**：技能库用 JSON 文件持久化，自优化用严格的棘轮逻辑保证单调不降。

This skill is the **engineering implementation** of both papers' ideas: the library is persisted as a JSON file, and self-optimization uses strict ratchet logic to guarantee monotonic non-decrease.

## 特性 Features

- ✅ 真的会把技能条目写入磁盘、支持查库复用、用棘轮逻辑守住「只留改进」。
- ✅ 零第三方依赖，纯标准库，跨平台（Windows / macOS / Linux）。
- ✅ 子命令式编排，便于在 Agent 工作流中流水线调用。
- ❌ 不自动写代码、不自动判断任务质量——验证分由你来给（用户评分 / LLM 自评 / 任务成功率）。
- ❌ 不做语义向量检索——`find` 是关键词 + 标签的轻量匹配；需要语义检索请外接向量库。
- ✅ 纯本地运行，零外部依赖，**无需任何 API Key / 网络**，国内无障碍（不调用 Claude 或任何外部服务）。

- ✅ Actually writes skill entries to disk, supports library reuse, and uses ratchet logic to hold the line on "keep only improvements."
- ✅ Zero third-party dependencies, pure standard library, cross-platform (Windows / macOS / Linux).
- ✅ Subcommand-style orchestration, easy to pipeline within agent workflows.
- ❌ Does not auto-write code or auto-judge task quality — you supply the validation score (user rating / LLM self-eval / task success rate).
- ❌ Does not do semantic vector retrieval — `find` is a lightweight keyword + tag match; bring your own vector store for semantic search.
- ✅ Runs purely locally with zero dependencies — **no API key or network needed**, works in China without blockers (does not call Claude or any external service).

## 适用受众 Who Is This For

面向**所有 Agent 用户**，从新手到专业编排者：
For **all agent users**, from beginners to professional orchestrators:

| 受众 Audience | 怎么用 How to use |
|------|--------|
| 新手 Beginner | 照抄下面「最小可运行示例」四行，换成自己的任务即可 / Copy the four-line minimal example below and swap in your own task |
| 进阶 Intermediate | 任务完成后 `add`，开工前 `find`，复盘 `record` + `optimize` / `add` after tasks, `find` before starting, `record` + `optimize` on review |
| 专业 Advanced | 把 `guard` 接进收尾自检、`audit` 接进 CI，用 `--max-steps` 约束自优化循环 / Wire `guard` into exit checks, `audit` into CI, bound loops with `--max-steps` |

## 安装 Installation

无需安装第三方包。语法兼容 Python 3.8+（开发实测 3.13）：
No third-party packages required. Syntax-compatible with Python 3.8+ (developed and tested on 3.13):

```bash
git clone https://github.com/KKWong3614/unclekk-skill-library.git skill-library
cd skill-library
python scripts/test_library.py   # 跑一遍自测，确认环境 OK / run the self-test to confirm the environment
```

期望末行输出 `ALL PASSED`。
Expect the last line to read `ALL PASSED`.

## 最小可运行示例 Minimal Runnable Example

四行跑通完整闭环（用临时库，不污染正式库）：
Four commands for a full loop (temp library, keeps your real one clean):

```bash
python scripts/library.py --store /tmp/demo.json add --task-type demo --description "写周报" --approach "拆解：本周进展→风险→下周计划" --tags "report" --score 0.6
python scripts/library.py --store /tmp/demo.json find --query "周报"
python scripts/library.py --store /tmp/demo.json optimize --id sl_001 --patch '{"approach":"拆解：本周进展→风险→下周计划→资源需求"}' --score 0.8
python scripts/library.py --store /tmp/demo.json guard
```

实测输出 / Actual output:

```
ADDED sl_001 (task_type=demo, baseline=0.6)
#sl_001 [demo] score=0.6 tags=['report']
   写周报
ACCEPTED sl_001: baseline 0.6 -> 0.8 (棘轮提升)
GUARD 步数: 2/50（剩余 48）
GUARD 闭环: 1/1（100%）
GUARD PASSED: 全部条目已闭环
```

## 快速上手 Quick Start

### 1. 沉淀（capture）

任务跑通后，把「怎么拆的、哪些维度是关键」存成条目：
After a task succeeds, store "how it was decomposed and which dimensions were key" as an entry:

```bash
python scripts/library.py add --task-type competitive_report \
  --description "做竞品分析报告" \
  --approach "按 Roadmap 拆解：市场定位/功能对比/定价" \
  --dimensions "市场定位,功能对比,定价策略" \
  --tags "report,competitor" --score 0.60
```

### 2. 复用（retrieve）

下次类似任务，先查库：
For the next similar task, query the library first:

```bash
python scripts/library.py find --query "竞品报告"
python scripts/library.py get --id sl_001
```

复用命中条目的 `approach`，只做行业相关的微调，不必从零开始。
Reuse the matched entry's `approach` with only industry-specific tweaks — no need to start from scratch.

### 3. 自优化（optimize · SkillOpt 棘轮）

复用后评估效果，用 `record` 记分；若发现更优的拆解方式，用 `optimize` 提出改动：
After reuse, evaluate the result and score it with `record`; if you find a better decomposition, propose a change with `optimize`:

```bash
python scripts/library.py record --id sl_001 --score 0.75
python scripts/library.py optimize --id sl_001 \
  --patch '{"approach":"按 Roadmap 拆解：市场定位/功能对比/定价/渠道"}' \
  --score 0.85
```

- 新分 `0.85 > 0.60` 基线 → **ACCEPTED**，改动写入。
- 若新分 `0.80`（未严格更高）→ **REJECTED**，改动回滚，库保持不变。

- New score `0.85 > 0.60` baseline → **ACCEPTED**, the change is written.
- If the new score is `0.80` (not strictly higher) → **REJECTED**, the change is rolled back and the library stays unchanged.

## 命令速查 Command Reference

| 命令 | 作用 | 计步 |
|------|------|------|
| `add` | 新增技能条目（`--task-type/--description/--approach/--dimensions/--tags/--score`） | ✅ |
| `find` | 按 `--query` / `--tags` 查库，返回命中条目；命中即标记已复用 | — |
| `get` | 查看单条完整内容；取出即标记已复用 | — |
| `list` | 列出全部条目，带 `CLOSED`/`OPEN` 闭环标记 | — |
| `record` | 记录一次使用结果分（`--id/--score/--note`） | ✅ |
| `optimize` | 提出改动补丁，严格提升才接受（`--id/--patch/--score`） | ✅ |
| `stats` | 库统计（条目数、平均分、闭环率、步数用量） | — |
| `guard` | 闭环守卫：有未闭环条目返回非 0（收尾自检 / CI） | — |
| `audit` | 输出 Markdown 审计报告 | — |
| `reset-steps` | 清零步数计数（撞上限后的兜底出口） | — |

| Command | Purpose | Counts |
|---------|---------|--------|
| `add` | Add a skill entry (`--task-type/--description/--approach/--dimensions/--tags/--score`) | ✅ |
| `find` | Query by `--query` / `--tags`; a hit marks the entry as reused | — |
| `get` | View a single entry's full content; retrieval marks it as reused | — |
| `list` | List all entries with `CLOSED`/`OPEN` loop flags | — |
| `record` | Record one usage result score (`--id/--score/--note`) | ✅ |
| `optimize` | Propose a change patch, accepted only on strict improvement (`--id/--patch/--score`) | ✅ |
| `stats` | Statistics (entry count, average score, loop-closure rate, step usage) | — |
| `guard` | Loop guard: returns non-zero if any entry is unclosed (exit check / CI) | — |
| `audit` | Emit a Markdown audit report | — |
| `reset-steps` | Reset the step counter (fallback exit after hitting the cap) | — |

全局参数：`--store <路径>`（默认 `~/.workbuddy/skill_library.json`）、`--max-steps <n>`（默认 50）。
Global flags: `--store <path>` (default `~/.workbuddy/skill_library.json`), `--max-steps <n>` (default 50).

## 硬代码保障 Hard-Coded Safeguards

四条约束全部由 `scripts/library.py` 强制执行，不是文档约定：
All four are enforced in code by `scripts/library.py`, not merely documented:

| 保障 Safeguard | 行为 Behavior | 退出码 Exit |
|------|-----------|--------|
| 步数限制 Step cap | 写操作累计计步并持久化；达到 `--max-steps`（默认 50）拒绝执行并中止，剩余 ≤5 步提前预警 / Write ops are counted and persisted; hitting `--max-steps` aborts, with a warning at ≤5 remaining | `2` |
| 严格闭环 Strict loop | 条目生命周期 `captured → reused → optimized`，缺一即 `OPEN`；`guard` 检出即失败 / Entry lifecycle must complete, else `OPEN`; `guard` fails on any | `1` |
| 兜底保障 Fallbacks | 每次中止都打印可执行的下一步动作，绝不裸抛堆栈 / Every abort prints actionable next steps, never a raw traceback | `1`/`2` |
| 白名单 Whitelist | `optimize` 补丁只能改 6 个业务字段，结构字段直接 `REJECTED` / Patches may touch only 6 business fields; structural fields are `REJECTED` | `1` |

审计报告完整样例见 `references/audit-sample.md`。
See `references/audit-sample.md` for full audit report samples.

## 目录结构 Directory Structure

```
skill-library/
├── SKILL.md                 # 技能定义（被 WorkBuddy / Agent 加载时读这个）
├── README.md                # 你正在看的这份
├── CHANGELOG.md             # 版本变更记录
├── scripts/
│   ├── library.py           # 编排器主程序（零依赖，含全部硬代码保障）
│   └── test_library.py      # 自测：沉淀→复用→棘轮→步数限制→闭环守卫
└── references/
    ├── schema.md            # 条目结构、生命周期字段与三阶段流程
    └── audit-sample.md      # 审计报告完整样例（PASS / ATTENTION 对照）
```

## 工作原理（三阶段闭环）How It Works (Three-Stage Loop)

```
   ┌──────────────┐   find/get    ┌──────────────┐
   │  capture     │ ───────────▶  │  retrieve    │
   │  add 沉淀    │               │  复用命中条目 │
   └──────────────┘               └──────────────┘
                                          │
                                          ▼
                                  ┌──────────────┐  仅当 score 严格提升
                                  │  optimize    │ ──────────▶ 写回库（只留改进）
                                  │  record+优化 │
                                  └──────────────┘
                                          │
                                          ▼
                                  ┌──────────────┐  三阶段缺一即 OPEN
                                  │  guard 卡口  │ ──────────▶ 非 0 退出，任务不得宣布完成
                                  └──────────────┘
```

每个条目必须走完 `captured → reused → optimized` 才算闭环；`guard` 是硬代码卡口。
Each entry must complete `captured → reused → optimized`; `guard` is the hard-coded gate.

## 许可 License

MIT © 2026 KK / 大叔笔记
