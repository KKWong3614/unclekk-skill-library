---
name: unclekk-skill-library
slug: unclekk-skill-library
displayName: UncleKK Skill Library · 让 Agent 把技能攒成库，越用越强
version: '1.3.0'
summary: 'Voyager 式终身技能库 + SkillOpt 式严格自优化：把成功任务的拆解方式与关键维度沉淀成可复用技能条目，新任务先查库复用、只在缺口补新能力；并用独立验证分做棘轮式自优化（严格提升才接受改动），让 Agent 跨任务积累经验、越用越强。 Voyager-style lifelong skill library + SkillOpt-style strict self-optimization: distill the decomposition method and key dimensions of successful tasks into reusable skill entries; new tasks first query the library to reuse, only adding new capabilities at gaps; and use independent validation scores for ratchet-style self-optimization (only accept changes on strict improvement), letting the Agent accumulate cross-task experience and grow stronger with use.'
description: Voyager 式技能库 + SkillOpt 式自优化。把成功任务的拆解方式与关键维度沉淀成可复用技能条目，新任务先查库复用、只在缺口补新能力；并用独立验证分做棘轮式自优化（严格提升才接受改动）。用于让 Agent 跨任务积累经验、越用越强。触发词：技能库、沉淀技能、复用 Roadmap、棘轮优化、自优化、capture、retrieve、skill library、optimize。
license: MIT
author: KK大叔 (UncleKK)
metadata:
  agent_created: true
  source: unclekk-harness/unclekk-skill-library
  category: agent-skill-library
---

# skill-library — 让 Agent 把技能攒成库，越用越强

**版本 v1.3.0** ｜ 纯本地 · 零第三方依赖 · 无需 API Key 与网络 ｜ English docs: `README.md`

把「这次任务是怎么拆的」存成条目，下次同类任务先查库复用；效果变好才允许改写条目（棘轮，只留改进）。

## 30 秒最小运行示例

复制这四行即可跑通完整闭环（`--store` 用临时库，不污染你的正式库）：

```bash
cd <本技能目录>
python scripts/library.py --store /tmp/demo.json add --task-type demo --description "写周报" --approach "拆解：本周进展→风险→下周计划" --tags "report" --score 0.6
python scripts/library.py --store /tmp/demo.json find --query "周报"
python scripts/library.py --store /tmp/demo.json optimize --id sl_001 --patch '{"approach":"拆解：本周进展→风险→下周计划→资源需求"}' --score 0.8
python scripts/library.py --store /tmp/demo.json guard
```

真实输出（已实测）：

```
ADDED sl_001 (task_type=demo, baseline=0.6)
#sl_001 [demo] score=0.6 tags=['report']
   写周报
ACCEPTED sl_001: baseline 0.6 -> 0.8 (棘轮提升)
GUARD 步数: 2/50（剩余 48）
GUARD 闭环: 1/1（100%）
GUARD PASSED: 全部条目已闭环
```

看到 `GUARD PASSED` 就说明装对了。去掉 `--store /tmp/demo.json` 即使用默认库 `~/.workbuddy/skill_library.json`。

## 这个技能适合谁

**面向所有 Agent 用户**，不同水平各取所需：

| 受众 | 怎么用 | 只需读 |
|------|--------|--------|
| **新手**（没写过脚本） | 照抄上面四行，把 `demo`/`写周报` 换成自己的任务 | 「30 秒最小运行示例」 |
| **进阶**（会用 CLI） | 任务完成后 `add` 沉淀，开工前 `find` 复用，复盘 `record`+`optimize` | 加读「三阶段工作流」「命令速查」 |
| **专业**（做 Agent 编排） | 把 `guard` 接进收尾自检，`audit` 接进 CI；用 `--max-steps` 约束自优化循环 | 加读「硬代码保障」「审计报告」 |
| **Agent 本体**（自动调用） | 按下方触发条件自动执行，无需用户显式下令 | 「自动触发条件」 |

不需要任何前置知识。环境要求：Python 3.8+（语法兼容，开发实测 3.13），无第三方包。

## 自动触发条件

Agent 满足以下任一条件应**自动**调用本技能，不必等用户开口：

| 时机 | 自动触发条件 | 自动执行 |
|------|--------------|----------|
| **开工前** | 收到一个有明确产出物的任务（报告/分析/方案/周报等） | `find --query <任务关键词>`，命中就复用 `approach` |
| **任务完成后** | 任务验收通过，且拆解方式具备可复用性（同类任务会再来） | `add` 沉淀拆解方式 + 关键维度 |
| **复用之后** | 用了库里条目完成任务 | `record --score <验证分>` 记真实效果 |
| **发现更优解** | 复用中找到更好的拆解方式，且新效果分**高于**条目基线 | `optimize` 提补丁，棘轮判定 |
| **收尾自检** | 准备向用户宣布任务完成前 | `guard`，未闭环不得宣布完成 |

用户显式触发词：技能库、沉淀技能、复用 Roadmap、棘轮优化、自优化、capture、retrieve、skill library、optimize。

## 能力边界（一眼看清）

**✅ 擅长处理**（直接交给它）
- 把「任务怎么拆的」存成条目，下次同类任务先查库复用，不从零开始。
- 用棘轮守住「只留改进」：新分严格高于基线才写回，退化自动回滚。
- 纯本地、零依赖、跨平台（Windows / macOS / Linux），不联网、不需 API Key，国内直接可用。

**⚠️ 需素材才有效**（缺了这些，库的质量就上不去）
- `--score` 要**你给**验证分（用户评分 / LLM 自评 / 任务成功率）；分数客观与否决定自优化质量，技能不替你打分。
- `--approach` 要**你写**可执行拆解（写「按 Roadmap 拆解：A→B→C」，不能写「研究一下」），写空被硬拒。
- `--tags` 要**你建**同义词标签组（都打 `competitor`），否则 `find` 字符匹配会漏同义词。
- 跨项目要**你用** `--store` 指定独立库，否则所有经验混在一个全局库里难以复用。

**❌ 超出范围**（别指望它做这些，附替代）
- 不自动写代码、不自动判断任务质量——验证分由你把控（见 FAQ Q2）。
- 不做语义检索：`find` 是字符重叠 + 标签匹配，同义词会漏 → 要语义检索请外接向量库（见 faq-deep D3）。
- 不是「把代码变成工具」的技能：它管理「任务拆解方式」经验，不改你的代码、不生成 MCP 工具。

## 安全与隐私

**禁止行为（硬规则）**
- 不读取、不外传库文件以外的任何文件；库只在你指定的 `--store` 路径读写。
- 不自动执行任何危险命令（`rm -rf`、格式化、改系统配置等）；本技能只操作自己的 JSON 库。
- 不要求、不存储他人账号密码与 API Key；`--score` 来源由你提供，技能不偷偷采集。
- 不把库内容当确定事实对外宣称——库是你的经验草稿，落地前需你验证。

**数据隐私**
- 条目只存「任务拆解方式 + 关键维度」这类经验，不存真实业务数据、密钥、个人信息。
- 误存了敏感信息：用 `optimize` 改掉该字段，或 `get --id <id>` 后手动删条目；彻底重置直接删库文件。
- 库文件属本地，建议不要把含敏感信息的版本提交到公开仓库。

**不胡编 + 决策可追溯**
- 所有 `ACCEPTED` 改动都基于你给的 `--score`，技能不替你编造效果；`REJECTED` 同样如实回滚。
- `audit` 报告每个指标都附「判读」，闭环 / 步数 / 接受次数一目了然，决策可复查。

## 硬代码保障（强制执行，不是口头约定）

以下四条全部写在 `scripts/library.py` 里由代码强制，Agent 无法用 prompt 绕过：

| 保障 | 硬代码行为 | 退出码 |
|------|-----------|--------|
| **步数限制** | 写操作（`add`/`record`/`optimize`）累计计步并持久化在库里；达到 `--max-steps`（默认 50）**拒绝执行并中止**，防自优化死循环。剩余 ≤5 步时提前预警 | `2` |
| **严格闭环** | 每条目有生命周期 `captured → reused → optimized`，缺一即 `OPEN`。`guard` 检出 OPEN 就失败，**任务不得宣布完成** | `1` |
| **兜底保障** | 任何中止都打印可执行的下一步（三选一动作），绝不裸抛堆栈；写盘失败翻译成权限/磁盘/换路径三步排查 | `1`/`2` |
| **白名单** | `optimize` 补丁只能改 6 个业务字段；触碰 `id`/`baseline_score` 等结构字段直接 `REJECTED` | `1` |

步数撞上限时的真实输出与兜底出口：

```
STOP: 步数已达上限 4/4，拒绝执行写操作 `add`（硬代码保障，防失控循环）。
      兜底动作，三选一：
        1. 先用 `audit` 看清库现状，确认这些写操作是否真的必要；
        2. 确认本轮任务已完成，用 `reset-steps` 清零计数后继续；
        3. 明确需要更多步数，用 `--max-steps 8` 提高上限。
```

## 三阶段工作流

理论出处：**Voyager**（NVIDIA + Caltech，终身技能库：查库→复用→只补缺口）+ **SkillOpt**（Microsoft，仅当严格提升才接受编辑）。本技能是这两篇的落地实现。

**1. capture 沉淀** — 任务跑通后，把「怎么拆的、哪些维度关键」存库：

```bash
python scripts/library.py add --task-type competitive_report \
  --description "做竞品分析报告" \
  --approach "按 Roadmap 拆解：市场定位/功能对比/定价" \
  --dimensions "市场定位,功能对比,定价策略" \
  --tags "report,competitor" --score 0.60
# → ADDED sl_001 (task_type=competitive_report, baseline=0.60)
```

`--approach` 必须可执行（写「按 Roadmap 拆解：A→B→C」，不能写「研究一下」），它是下游复用的核心输入，写空会被硬拒。

**2. retrieve 复用** — 新任务先查库，命中就用，不从零开始：

```bash
python scripts/library.py find --query "竞品报告"    # 列出命中条目
python scripts/library.py get --id sl_001            # 看完整 approach
```

返回 `NO MATCH` 说明库里没有，此时回退到第 1 步从零拆解，**不要硬用不相关条目**。

**3. optimize 自优化（棘轮）** — 复用后记分；发现更优解才提改动：

```bash
python scripts/library.py record --id sl_001 --score 0.75
python scripts/library.py optimize --id sl_001 \
  --patch '{"approach":"按 Roadmap 拆解：市场定位/功能对比/定价/渠道"}' --score 0.85
# → ACCEPTED sl_001: baseline 0.6 -> 0.85 (棘轮提升)
```

新分 `0.85 > 0.60` → **ACCEPTED** 写入；若给 `0.80`（未严格高于新基线 0.85）→ **REJECTED** 并回滚，库保持不变。这就是「只留改进」。

三轮实战节奏：第一次做完 `add`；第二次 `find` 命中直接复用，两小时活压到二十分钟；第三次发现某维度失效，`optimize` 提改动，只有真更优才写回。

## 命令速查

| 命令 | 作用 | 计步 |
|------|------|------|
| `add` | 新增条目（`--task-type/--description/--approach/--dimensions/--tags/--score`） | ✅ |
| `find` | 按 `--query`/`--tags` 查库，`--top` 控条数（默认 3）；命中即标记已复用 | — |
| `get` | 看单条完整内容（`--id`）；取出即标记已复用 | — |
| `list` | 列出全部，带 `CLOSED`/`OPEN` 闭环标记 | — |
| `record` | 记一次使用结果分（`--id/--score/--note`） | ✅ |
| `optimize` | 提改动补丁，严格提升才接受（`--id/--patch/--score`） | ✅ |
| `stats` | 统计：条目数、平均分、闭环率、步数用量 | — |
| `guard` | 闭环守卫，有 OPEN 返回非 0（收尾自检 / CI 用） | — |
| `audit` | 输出 Markdown 审计报告 | — |
| `reset-steps` | 清零步数计数（撞上限后的兜底出口） | — |

全局参数：`--store <路径>`（默认 `~/.workbuddy/skill_library.json`）、`--max-steps <n>`（默认 50）。

**定制化**：用 `--store` 给不同项目开独立库；用 `--tags` 建同义词标签组；用 `--dimensions` 捕捉你所在领域的专属关键维度；用 `--max-steps` 约束自优化强度。详见 faq-deep D6 / D7。

## 审计报告

`audit` 输出 Markdown 报告，含总览、条目明细、风险处置、PASS/ATTENTION 结论。真实样例（健康库）：

```
| 指标 | 值 | 判读 |
|------|-----|------|
| 条目数 | 2 | 正常 |
| 步数用量 | 1/50 | 健康 |
| 闭环率 | 2/2 | ✅ 全闭环 |
| 平均分 | 0.78 | 越高越稳 |
| 累计接受改动 | 2 | 棘轮生效次数 |
...
**PASS** — 库健康，可继续使用。
```

**完整报告样例（健康库 PASS + 异常库 ATTENTION 双向对照，含每个字段怎么读、发现问题怎么处置）见 `references/audit-sample.md`。**

## 常见坑点与 FAQ

每条都给可直接跑的命令。字段结构见 `references/schema.md`，反模式见 `references/anti-patterns.md`，深度边缘场景（垂直领域 / 工具兼容 / 定制化 / 数据安全 / 商用授权）见 `references/faq-deep.md`。

**Q1 库在哪？怎么换位置？**
默认 `~/.workbuddy/skill_library.json`（Windows：`C:\Users\<你>\.workbuddy\skill_library.json`）。换位置：`python scripts/library.py --store D:/my_lib.json list`（`--store` 要放在子命令**前面**）。

**Q2 `--score` 填什么？**
0-1 的验证分比例，来源自选（用户评分 / LLM 自评 / 任务成功率）。**坑点**：填 `1.5` 或 `"很好"` 会硬拒退出——`ERROR: --score 必须在 0-1 之间…收到: 1.5`。

**Q3 `find` 搜不到我的条目？**
`find` 是**字符重叠**匹配，不是语义检索。**坑点实例**：搜「竞争分析」找不到「竞品报告」（只重叠「竞」字）；反过来搜「竞品报告」会误命中含「竞争」的储能条目。对策：① `--tags` 建同义词标签（都打 `competitor`）；② 先 `list` 看全部；③ 需要语义检索请外接向量库。

**Q4 `optimize` 一直 REJECTED？**
不是 bug，是棘轮生效：新分必须**严格大于** `baseline_score`。先 `get --id sl_001` 看当前 baseline，再给真实更高分。**坑点**：不要为了通过硬凑分，那等于把退化写进库。

**Q5 报 `STOP: 步数已达上限`？**
硬代码防死循环。三选一：`audit` 复核必要性 → `reset-steps` 清零 → `--max-steps 100` 提高上限。**坑点**：`optimize` 被 REJECTED 也计步（防无限重试），所以反复凑分会快速耗尽步数。

**Q6 `guard` 报 OPEN / GUARD FAILED？**
说明条目没走完 `captured→reused→optimized`。看它打印的兜底动作照做即可：缺 `reused` 就 `get --id <id>`，缺 `optimized` 就 `record` + `optimize`。**坑点**：只 `add` 不复用的条目永远 OPEN——库不是垃圾桶，存了就要用。

**Q7 patch 里改 `id` 或 `baseline_score`？**
直接拒绝：`REJECTED sl_001: 拒绝非法字段 ['id']`。只能改 `approach`/`description`/`task_type`/`tags`/`key_dimensions`/`usage_notes` 六个字段。

**Q8 多个 Agent 同时写一个库？**
可能读到过期数据、丢条目。串行调用，或各用不同 `--store`。已发生就看条目 `edits` 时间戳定位冲突。

**Q9 库损坏 / 想重置？**
损坏时会打印 WARNING 并新建空库，恢复看同目录 `skill_library.json.tmp`（原子写留下的临时文件）改名即可。彻底重置：直接删库文件，下次命令自动新建。

**Q10 需要联网 / API Key 吗？国内能用吗？**
都不需要。纯本地、零外部依赖、不调用任何外部 API，国内无障碍。

## 文件说明

| 文件 | 内容 |
|------|------|
| `scripts/library.py` | 编排器主程序（零依赖），含全部硬代码保障 |
| `scripts/test_library.py` | 自测，覆盖沉淀→复用→棘轮→步数限制→闭环守卫全链路 |
| `references/schema.md` | 条目字段结构、生命周期字段、三阶段流程 |
| `references/audit-sample.md` | 审计报告完整样例（PASS / ATTENTION 双向对照） |
| `references/anti-patterns.md` | 反模式与禁忌用法（对照改进） |
| `references/faq-deep.md` | 深度 FAQ：垂直领域 / 工具兼容 / 定制化 / 数据安全 / 商用授权 |
| `README.md` | 项目说明与 English docs |
| `CHANGELOG.md` | 版本变更记录 |

运行时生成的 `skill_library.json` 是你自己长出来的库，**不属于本技能发布内容**。

自测（改完代码务必跑）：`python scripts/test_library.py` → 期望末行 `ALL PASSED`。
