# skill-library · 让 Agent 把技能攒成库，越用越强

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

- ✅ Actually writes skill entries to disk, supports library reuse, and uses ratchet logic to hold the line on "keep only improvements."
- ✅ Zero third-party dependencies, pure standard library, cross-platform (Windows / macOS / Linux).
- ✅ Subcommand-style orchestration, easy to pipeline within agent workflows.
- ❌ Does not auto-write code or auto-judge task quality — you supply the validation score (user rating / LLM self-eval / task success rate).
- ❌ Does not do semantic vector retrieval — `find` is a lightweight keyword + tag match; bring your own vector store for semantic search.

## 安装 Installation

无需安装第三方包。要求 Python 3.10+：
No third-party packages required. Needs Python 3.10+:

```bash
git clone https://github.com/KKWong3614/unclekk-skill-library.git skill-library
cd skill-library
python scripts/test_library.py   # 跑一遍自测，确认环境 OK
```

```bash
git clone https://github.com/KKWong3614/unclekk-skill-library.git skill-library
cd skill-library
python scripts/test_library.py   # run the self-test to confirm the environment is OK
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

| 命令 | 作用 |
|------|------|
| `add` | 新增技能条目（`--task-type/--description/--approach/--dimensions/--tags/--score`） |
| `find` | 按 `--query` / `--tags` 查库，返回命中条目 |
| `get` | 查看单条完整内容 |
| `list` | 列出全部条目 |
| `record` | 记录一次使用结果分（`--id/--score/--note`） |
| `optimize` | 提出改动补丁，严格提升才接受（`--id/--patch/--score`） |
| `stats` | 库统计（条目数、平均分、最高/最低分） |

| Command | Purpose |
|---------|---------|
| `add` | Add a skill entry (`--task-type/--description/--approach/--dimensions/--tags/--score`) |
| `find` | Query the library by `--query` / `--tags`, return matched entries |
| `get` | View a single entry's full content |
| `list` | List all entries |
| `record` | Record one usage result score (`--id/--score/--note`) |
| `optimize` | Propose a change patch, accepted only on strict improvement (`--id/--patch/--score`) |
| `stats` | Library statistics (entry count, average score, max/min score) |

所有命令支持 `--store <路径>` 指定库文件，默认 `~/.workbuddy/skill_library.json`。
All commands support `--store <path>` to specify the library file; default is `~/.workbuddy/skill_library.json`.

## 目录结构 Directory Structure

```
skill-library/
├── SKILL.md              # 技能定义（被 WorkBuddy / Agent 加载时读这个）
├── README.md             # 你正在看的这份
├── LICENSE               # MIT
├── .gitignore
├── scripts/
│   ├── library.py         # 编排器主程序（零依赖）
│   └── test_library.py    # 自测：沉淀→查库→棘轮自优化全链路
└── references/
    └── schema.md          # 条目结构与三阶段流程说明
```

## 工作原理（三阶段闭环）How It Works (Three-Stage Loop)

```
   ┌─────────────┐    find/get    ┌─────────────┐
   │  capture     │ ────────────▶ │  retrieve    │
   │  add 沉淀    │               │  复用命中条目 │
   └─────────────┘               └─────────────┘
                                     │
                                     ▼
                               ┌─────────────┐  仅当 score 严格提升
                               │  optimize     │ ────────────▶ 写回库（只留改进）
                               │  record+优化  │
                               └─────────────┘
```

## 许可 License

[MIT](LICENSE) © 2026 KK / 大叔笔记
[MIT](LICENSE) © 2026 KK / 大叔笔记
