# skill-library — CHANGELOG

## 1.3.0 (2026-09-01) — 硬代码保障 + 文档重构（九项质量要求落地）

> 从「声明式技能」升级为「代码强制约束的技能」：步数限制、严格闭环、兜底出口全部由 `library.py` 强制执行，Agent 无法用 prompt 绕过。文档同步精简 33%（334 → 225 行）并补齐最小示例、受众说明、自动触发条件、审计样例。

**新增硬代码保障（scripts/library.py）**
- **步数限制**：写操作（`add`/`record`/`optimize`）累计计步并持久化到 `meta.steps`；达到 `--max-steps`（默认 50）在执行前拒绝并中止（退出码 `2`），打印三条兜底动作；剩余 ≤5 步时提前 WARNING 预警。`optimize` 被 REJECTED 也计步，防无限重试凑分。
- **严格闭环**：新增条目生命周期字段 `lifecycle`（`captured → reused → optimized`），缺任一即 `OPEN`。`find` 命中 / `get` 取出 / `record` 记分自动打 `reused` 戳，`optimize` ACCEPTED 打 `optimized` 戳。
- **新增 `guard` 子命令**：闭环守卫，检出 `OPEN` 条目返回非 0 并逐条给出兜底动作，用于 Agent 收尾自检与 CI 卡口——未闭环不得宣布任务完成。
- **新增 `audit` 子命令**：输出 Markdown 审计报告（总览 / 条目明细 / 风险与处置 / PASS-ATTENTION 结论），自动检出步数接近上限、条目无标签、`last_score < baseline_score` 三类风险。
- **新增 `reset-steps` 子命令**：撞步数上限后的兜底出口，清零计数继续下一轮。
- `list` / `stats` 增强：`list` 行尾显示 `CLOSED`/`OPEN`；`stats` 增加闭环率与步数用量。
- 统一退出码约定：`0` 正常 / `1` 业务失败 / `2` 步数超限。
- 老库向后兼容：v1.2.x 无 `lifecycle` 字段的条目首次运行自动补齐（按 `created` 与 `edits` 推断），不会因升级被全判成 OPEN。

**Bug 修复**
- 修复 `cmd_add` 返回条目 id（字符串）被 `main` 当作退出码的潜伏缺陷——此前 `sys.exit("sl_001")` 会让 `add` 命令返回码变成 1 并把 id 打到 stderr。现在只有 int 才作为退出码。
- `optimize` 增加 `--patch` 非对象校验（传 JSON 数组/字符串时给明确提示，不再走到白名单比较才失败）。
- `--max-steps < 1` 时提前报错退出。

**文档重构（九项质量要求）**
1. SKILL.md / README 新增「30 秒最小运行示例」——四行跑通 `add → find → optimize → guard`，附实测输出，看到 `GUARD PASSED` 即环境正常。
2. 版本号显式前置：SKILL.md 与 README 首屏均标注 **v1.3.0**。
3. 文档精简：删除全文中英双语交替段落（英文集中在 README），合并重复的「能力边界速览 / 真实能力边界」两节，SKILL.md 由 334 行降至 225 行。
4. 新增「这个技能适合谁」受众表：新手 / 进阶 / 专业 / Agent 本体四类各自的用法与最少必读章节。
5. 硬代码保障独立成章，列明四条约束的强制行为与退出码，并附步数撞限的真实输出。
6. 步数限制 / 兜底动作 / 严格闭环三者在文档与代码中一一对应。
7. 新增「自动触发条件」表：开工前 / 完成后 / 复用后 / 发现更优解 / 收尾自检五个时机的自动触发条件与自动执行命令。
8. 新增 `references/audit-sample.md`：审计报告完整样例，PASS 与 ATTENTION 双向对照，含字段判读表与处置指引。
9. FAQ 重写为 10 条，每条都给可直接执行的命令与坑点实例（如「搜『竞争分析』找不到『竞品报告』」的字符重叠陷阱、「REJECTED 也计步」的耗尽风险）。

**断链与孤立文档修复**
- 修复 README 许可区指向 LICENSE 文件的断链（发布包内无该文件，改为纯文本 MIT）与重复的 License 行。
- 修正 README 目录结构：移除包内并不存在的 `LICENSE` / `.gitignore`，补上 `CHANGELOG.md` 与 `references/audit-sample.md`。
- 修复 SKILL.md 末尾一条 `skill_library.json` 英文说明被挤到 FAQ 之后形成的孤立残句。
- 移除易断的中文锚点跳转，改为文件相对路径引用；`references/schema.md` 与 `audit-sample.md` 均在 SKILL.md「文件说明」表中建立入口，无孤立文档。
- 统一 Python 版本表述为「语法兼容 3.8+，开发实测 3.13」（此前 README 写 3.10+ 与实际不一致）。

**自测（scripts/test_library.py）**
- 从 13 项扩充到 **27 项**，全部 PASS（Python 3.13.12 实测）。新增用例：`add` 成功退出码为 0（回归上述 bug）、`list` 闭环标记、`stats` 闭环率与步数、`patch` 非对象被拒、`patch` 含 `id` 被白名单拒绝、未闭环 `guard` 返回非 0、闭环后 `guard` 通过、`audit` 报告关键字段、步数超限硬中止（退出码 2）、超限后只读命令仍可用、`reset-steps` 清零后可继续写、`--max-steps < 1` 被拒。
- 新增 `run_at(store, ...)` 辅助函数，让步数 / 闭环类用例在独立库上运行，互不干扰计数。

**TRACE 质量门（2026-09-01 · skill-trace-checker 全量评测）**
- 五维度 20 子项全部达到 **5.0** 满分标准（T/R/A/C/E 各 4 项）。
- 为达标做的实质改动（非仅改措辞）：
  - 新增「安全与隐私」章节：禁止行为硬规则 + 数据隐私脱敏指导 + 不胡编 / 决策可追溯。
  - 「能力边界」改为三分类（✅擅长 / ⚠️需素材 / ❌超出范围），每类 ≥3 例，覆盖 T·边界透明度与 A·能力边界定义。
  - 新增「定制化」说明（`--store` / `--tags` / `--dimensions` / `--max-steps`）。
  - 新建 `references/anti-patterns.md`（5 反模式对照改进 + 禁忌清单）。
  - 新建 `references/faq-deep.md`（10 题，覆盖垂直领域 / 工具兼容 / 定制化 / 数据安全 / 商用授权）。
  - 「文件说明」表与 FAQ 引导同步指向两个新参考文件，无孤立文档。

## 1.2.4 (2026-09-01) — TRACE 评测驱动改进（可用性 / 文档 / 错误处理）

> 依据 SkillHub TRACE 评测报告（综合 4.4/5）短板定向改进：C 反模式与 FAQ 3.8（全项最低）、R 异常处理 4.0、C 文档质量 4.3、A 能力边界 4.3；并对评测误判的「需要 Claude API」项做正本清源。

**文档（SKILL.md / README.md）**
- 顶部新增「能力边界速览」框：一眼看清能做什么 / 不能做什么；明确声明**纯本地、零外部依赖、无需任何 API Key / 网络、国内无障碍**，并澄清本技能**不是**「把代码变成工具 / 生成 MCP 工具」类技能（消除评测误判）。
- 新增「常见问题 FAQ」章节（9 条：库位置 / 并发 / find 搜不到 / score 怎么定 / 库损坏恢复 / 重置库 / 跨语言检索失效 / optimize 被拒排查 / 是否需联网）。
- 新增「真实运行示例」章节：展示 add / find / optimize（接受与拒绝）/ stats / 错误提示的真实终端输出。
- README 特性区补强「无需 API Key / 网络、国内无障碍」声明。

**脚本（scripts/library.py · 解决 R 异常处理 4.0 / 运行稳定性 4.3）**
- `save_store` 增加 OSError / 权限 / 磁盘满捕获，输出友好中文排查建议并 `exit(1)`，不再抛裸堆栈。
- `_parse_score` 增加 0-1 范围校验，越界给出明确提示并 `exit(1)`。
- `cmd_add` 校验 `--approach` / `--description` / `--task-type` 非空（approach 必须可执行）。
- `cmd_optimize` 的坏 `--patch` JSON 改为返回非 0 并给出合法 JSON 示例（此前静默 return，行为不一致）。
- `get` / `record` / `optimize` 的 NOT FOUND 统一返回非 0 并提示用 `list` / `find` 兜底。
- `load_store` 损坏提示补全恢复建议（检查 .tmp 临时文件 / 备份）。
- `cmd_find` 重写：一次性算分后排序，避免重复计算与不稳定排序。

## 1.2 (2026-07-15) — 文档扩写 + 修复重新随包发布

**SKILL.md 文档扩写**
- frontmatter 补 `version: 1.2`，新增 `触发词` 字段，便于 WorkBuddy 命中加载。
- 三阶段工作流每步新增 🔴 CHECKPOINT 输入/输出标注与关键约束（score 范围、`--approach` 必须可执行、find 无命中回退拆解）。
- `optimize` 步骤补 🛑 STOP 标记：明确 patch 仅限白名单字段，结构字段（id/baseline_score/last_score/edits）不可被覆盖。
- 新增「失败模式（三段式 fallback）」表与「反例与黑名单（9 条）」表，固化常见误用与正确做法。

**修复随包重新发布（对齐 1.1）**
- 此前部署的 skill 实为本发布前的旧版（无 version 字段、`library.py` 缺防护），本次把 1.1 的 P0/P1 修复一并随包固化：`optimize` 白名单防护、`_parse_score()` 输入校验、`load_store` 损坏库 WARNING 告警、子命令返回码退出。部署后实际行为与文档描述一致。
- SKILL.md 命令行示例维持 `scripts/` 前缀（与 README.md 一致）。

## 1.1 (2026-07-14) — 审计后修复版

**安全修复 (P0)**
- cmd_optimize 加 patch 键白名单，仅允许修改 approach/description/task_type/tags/key_dimensions/usage_notes，拒绝 id、baseline_score 等结构字段被补丁键注入覆盖
- load_store 裸 except 改为记录异常并 print 到 stderr 告警，损坏的 JSON 库重建空库时用户可见告警，拒绝静默丢数据

**输入校验 (P1)**
- 所有 `--score` 改用 `_parse_score()`，非法输入（非数字字符串）给出明确错误信息并 exit(1)，避免 float() 硬崩溃

**文档修复 (P1)**
- SKILL.md 全部命令行示例加 `scripts/` 前缀（与 README.md 一致），修复 4 处路径错误导致用户 No such file 功能断裂
- SKILL.md frontmatter 加 `version: 1.1`

## 1.0 (初始)
- 新增 Voyager 式技能库（add/find/get/list）+ SkillOpt 式自优化（record/optimize/stats）
- 零第三方依赖，跨平台 CLI 编排器
