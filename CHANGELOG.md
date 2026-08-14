# skill-library — CHANGELOG

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
