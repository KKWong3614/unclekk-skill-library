---
name: unclekk-skill-library
slug: unclekk-skill-library
displayName: UncleKK Skill Library · 让 Agent 把技能攒成库，越用越强
version: '1.2'
summary: Voyager 式终身技能库 + SkillOpt 式严格自优化：把成功任务的拆解方式与关键维度沉淀成可复用技能条目，新任务先查库复用、只在缺口补新能力；并用独立验证分做棘轮式自优化（严格提升才接受改动），让 Agent 跨任务积累经验、越用越强。
description: Voyager 式技能库 + SkillOpt 式自优化。把成功任务的拆解方式与关键维度沉淀成可复用技能条目，新任务先查库复用、只在缺口补新能力；并用独立验证分做棘轮式自优化（严格提升才接受改动）。用于让 Agent 跨任务积累经验、越用越强。触发词：技能库、沉淀技能、复用 Roadmap、棘轮优化、自优化、capture、retrieve、skill library、optimize。
license: MIT
author: KK大叔 (UncleKK)
metadata:
  agent_created: true
  source: unclekk-harness/unclekk-skill-library
  category: agent-skill-library
---

# skill-library：让 Agent 把技能攒成库，越用越强

## 理论来源（与「读论文造技能 之三」对应）
- **Voyager（NVIDIA + Caltech）**：给 Agent 建一个终身技能库。每次成功解决任务，把关键操作写成可复用技能条目存进去；下次遇到类似任务，先查库、再复用、只在缺口处补新能力。
- **SkillOpt（Microsoft）**：技能怎么变强。每次使用技能后用独立验证分评估；只有严格提升时才接受对技能的修改——只留改进，不留退化。

本技能是这两篇论文的**落地实现**：技能库用 JSON 文件持久化，自优化用严格的棘轮逻辑保证单调不降。

## 真实能力边界（务必读）
- ✅ 本技能**真的会**把技能条目写入磁盘、支持查库复用、并用棘轮逻辑守住「只留改进」。
- ✅ 子命令零第三方依赖，跨平台（Windows / macOS / Linux）。
- ❌ 本技能**不会**自动写代码、不会自动判断任务质量。验证分（`--score`）由你来给——可以是用户评分、LLM 自评、或任务成功率。分数来源的客观性决定自优化的质量。
- ❌ 本技能**不做**语义向量检索。`find` 是关键词 + 标签的轻量匹配，足够多数场景；需要语义检索请外接向量库。
- 典型用法：Agent 在完成任务后调用 `add` 沉淀，开工前 `find` 复用，复盘时 `record` + `optimize` 做自优化。

🔴 CHECKPOINT：确认当前库文件路径（默认 `~/.workbuddy/skill_library.json`），如要指定路径请用 `--store <路径>`。

## 三阶段工作流

### 1. capture 沉淀

**输入**：完成的任务 + 拆解方式 + 关键维度 + 标签 + 基线验证分
**输出**：库中新增一个技能条目（id 由系统自动分配，如 sl_001）

任务跑通后，把「怎么拆的、哪些维度是关键」存成条目：

```
python scripts/library.py add --task-type competitive_report \
  --description "做竞品分析报告" \
  --approach "按 Roadmap 拆解：市场定位/功能对比/定价" \
  --dimensions "市场定位,功能对比,定价策略" \
  --tags "report,competitor" --score 0.60
```

🔴 CHECKPOINT：`--score` 必须是 0-1 之间的数字，传非数字会报错退出。`--approach` 必须可执行（不能写"研究一下"这类模糊词），它是下游复用的核心输入。

### 2. retrieve 复用

**输入**：新任务的关键词 / 标签
**输出**：命中条目（按匹配分降序），最多返回 `--top` 条（默认 3）

下次类似任务，先查库：

```
python scripts/library.py find --query "竞品报告"
python scripts/library.py get --id sl_001
```

复用命中条目的 `approach`，只做行业相关的微调，不必从零开始。

🔴 CHECKPOINT：如果 `find` 返回 `NO MATCH`，说明库中无相关条目，此时应当回退到从零拆解（第 1 阶段 capture），而不是硬用不相关的条目。

### 3. optimize 自优化（SkillOpt 棘轮）

**输入**：条目 id + JSON 补丁（仅允许修改 approach/description/task_type/tags/key_dimensions/usage_notes）+ 新验证分
**输出**：ACCEPTED（改动写入、基线提升）或 REJECTED（改动回滚、库保持不变）

复用后评估效果，用 `record` 记分；若发现更优的拆解方式，用 `optimize` 提出改动：

```
python scripts/library.py record --id sl_001 --score 0.75
python scripts/library.py optimize --id sl_001 \
  --patch '{"approach":"按 Roadmap 拆解：市场定位/功能对比/定价/渠道"}' \
  --score 0.85
```

- 新分 `0.85 > 0.60` 基线 → **ACCEPTED**，改动写入。
- 若新分 `0.80`（未严格更高）→ **REJECTED**，改动回滚，库保持不变。

🛑 STOP：`optimize` 的 patch 只能改白名单内的字段（approach / description / task_type / tags / key_dimensions / usage_notes）。`id`、`baseline_score`、`last_score`、`edits` 等结构字段会被拒绝。不要试图覆盖它们。

## 竞品报告三轮示例（对应文章）
1. **第一次做**：按 Roadmap 拆解生成报告，`add` 把拆解方式 + 常用维度存库。
2. **第二次做**：`find` 命中，`get` 复用上一份 Roadmap，只做行业微调——两小时活压缩到二十分钟。
3. **第三次做**：复用中发现某维度效果变差，提出改动并 `optimize`；只有确实更优才写回库。

## 命令速查

| 命令 | 作用 |
|------|------|
| `add` | 新增技能条目（--task-type/--description/--approach/--dimensions/--tags/--score） |
| `find` | 按 --query / --tags 查库，返回命中条目 |
| `get` | 查看单条完整内容 |
| `list` | 列出全部条目 |
| `record` | 记录一次使用结果分（--id/--score/--note） |
| `optimize` | 提出改动补丁，严格提升才接受（--id/--patch/--score） |
| `stats` | 库统计（条目数、平均分、最高/最低分） |

所有命令支持 `--store <路径>` 指定库文件，默认 `~/.workbuddy/skill_library.json`。

## 失败模式（三段式 fallback）

| 场景 | 触发条件 | 一线修复 | 仍失败兜底 |
|------|----------|----------|------------|
| `find` 无命中 | 库中无匹配条目的关键词/标签 | 改小 `--query` 关键词范围，或换 `--tags` 只查标签 | 放弃复用，回退到第 1 阶段从零拆解 |
| `optimize` 被 REJECTED | 新分未严格高于基线 | 确认补丁真的改善了效果，再给更高的验证分 | 放弃本次改动，保留原基线；不要硬凑分 |
| JSON 库文件损坏 | 库文件被意外截断/非法 JSON | 命令会输出 WARNING 并新建空库；检查最近是否有并发写入 | 从备份或 `--store` 换一个干净路径重建库 |
| `--score` 输入非法 | 传入非数字字符串（如 "abc"） | 改为 0-1 之间的数字（如 0.75） | `add` 不传则用默认 0.0；`record`/`optimize` 为必填，不传则命令直接报错退出 |
| 磁盘满 / 权限不足 | 库所在目录不可写 | 检查磁盘空间；确认 `~/.workbuddy/` 目录权限 | 用 `--store <其他路径>` 指定可写目录 |
| 并发多进程同时 add | 两个 Agent 同时写入同一库文件 | 避免并发；串行调用 | 如已发生，检查 `edits` 时间戳定位冲突条目 |

## 反例与黑名单（不要这样做）

| # | 反模式 | 后果 | 正确做法 |
|---|--------|------|----------|
| 1 | `--score` 传非数字（"abc"/"很好"） | 命令硬崩溃，进程退出 | 传 0-1 数字，如 0.75 |
| 2 | `--approach` 写模糊词（"研究一下""一些东西"） | 下游 `get` 拿到不可执行的产出，复用失败 | 写具体步骤，如"按 Roadmap 拆解：A→B→C" |
| 3 | patch 里覆盖 `id` / `baseline_score` | 键被白名单拒绝，改动无效果 | 只改白名单字段（approach/description/task_type/tags/key_dimensions/usage_notes） |
| 4 | 绕过规划直接执行，不先用 `find` 查库 | 漏掉已有经验，重复造轮子 | 开工前必须 `find`，无命中再拆解 |
| 5 | 并发多进程同时 `add` / `optimize` 同一库 | 可能读过期 data 写入，条目丢失 | 串行调用，或用 `--store` 各自独立库 |
| 6 | 用 `record` 记比基线更差的分当"优化" | baseline 与 last_score 语义割裂，后续 optimize 边界模糊 | `record` 用于记录真实使用分；`optimize` 才是棘轮入口 |
| 7 | 跳过 `--dimensions` 或 `--tags` 留空 | 查库时匹配精度下降（靠字符重叠，无标签加成） | 至少填 1-2 个标签，便于后续检索 |
| 8 | 用关键词匹配替代语义检索 | 跨语言/同义词/概念相近时查库失效（如搜"竞争分析"找不到"竞品报告"） | 对需要语义检索的场景，外接向量库或用 `--tags` 建立同义词标签表 |
| 9 | `record` 记分但跳过 `optimize` | 基线永不提升，棘轮失效，技能库只记不退 | `record` + `optimize` 必须成对使用，每次记分后至少评估一次是否优化 |

## 文件说明
- `scripts/library.py`：编排器主程序（零依赖）。
- `scripts/test_library.py`：自测，覆盖沉淀→查库→棘轮自优化全链路。
- `references/schema.md`：条目结构与三阶段流程说明。
- `skill_library.json`：运行时由 agent 自己长出来的技能库，**不属于本技能发布内容**；`results.tsv` 之类的审计痕迹也不在此技能内。
