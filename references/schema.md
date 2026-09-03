# 条目结构与数据模型（skill_library.json）

适用版本 v1.3.0。命令总表与 FAQ 见上层 `SKILL.md`，审计报告样例见 `audit-sample.md`。

库是单个 JSON 文件，顶层两个键：

```json
{
  "entries": { "sl_001": { ...条目... } },
  "meta": { "created": "ISO时间", "version": 1, "steps": 4 }
}
```

## meta 字段

| 字段 | 含义 |
|------|------|
| `created` | 库创建时间（ISO） |
| `version` | 库结构版本号 |
| `steps` | **累计写操作步数**（`add`/`record`/`optimize` 各 +1，只读命令不计）。达到 `--max-steps` 时硬中止；`reset-steps` 可清零 |

## 单条技能条目字段

| 字段 | 含义 |
|------|------|
| `id` | 自动生成，如 `sl_001` |
| `task_type` | 任务类型键，如 `competitive_report` |
| `description` | 这条技能解决什么任务 |
| `approach` | 可复用的拆解方式 / Roadmap（核心沉淀物，必须可执行） |
| `key_dimensions` | 关键分析维度数组 |
| `tags` | 检索标签数组 |
| `baseline_score` | 上次「被接受的改动」对应的验证分（棘轮基线） |
| `last_score` | 最近一次记录的使用分 |
| `edits` | 被接受的改动历史 `[{at, patch, score}]` |
| `usage_notes` | `record --note` 追加的使用备注 `[{at, note, score}]` |
| `lifecycle` | **生命周期戳**，见下节 |
| `created` / `updated` | ISO 时间戳 |

## lifecycle 生命周期（闭环判定依据）

```json
"lifecycle": {
  "captured":  "2026-09-01T21:52:01+08:00",
  "reused":    "2026-09-01T21:52:02+08:00",
  "optimized": "2026-09-01T21:52:02+08:00"
}
```

| 阶段 | 何时打戳 | 缺失时的兜底动作 |
|------|----------|------------------|
| `captured` | `add` 成功 | 重新 `add`（异常情况，通常不会缺） |
| `reused` | `find` 命中 / `get` 取出 / `record` 记分 | `get --id <id>` 或 `find --query <关键词>` |
| `optimized` | `optimize` 被 ACCEPTED | `record` 记分后 `optimize` 提改动 |

三个戳齐全 = `CLOSED`，缺任一 = `OPEN`。打戳幂等，不覆盖首次时间。
`guard` 检出 `OPEN` 即返回非 0，`list` 会在行尾显示 `CLOSED`/`OPEN`。

**向后兼容**：v1.2.x 老库没有 `lifecycle` 字段，首次运行会自动补齐——按 `created` 推断 `captured`，若已有 `edits` 则据其时间戳补 `reused`/`optimized`，不会因升级把老条目全判成 OPEN。

## 三阶段工作流

1. **capture（沉淀）**：完成任务后 `add`，把拆解方式 + 关键维度存库。
2. **retrieve（复用）**：新任务前 `find`，复用命中条目的 `approach`，只补缺口。
3. **optimize（自优化）**：复用后 `record` 打分；`optimize` 提改动，仅当新分**严格大于** `baseline_score` 才接受，否则回滚。

收尾必须跑 `guard`：未闭环不得宣布任务完成。

## 棘轮纪律

`optimize` 的接受条件是 `new_score > baseline_score`（严格大于）。
等于或更低 → 拒绝并回滚，保证技能分数随时间单调不降。这与论文 SkillOpt 的「仅当严格提升才接受编辑」一致。

被 REJECTED 也会计步（防无限重试凑分）。

## optimize 补丁字段白名单

只允许修改这 6 个字段：`approach`、`description`、`task_type`、`tags`、`key_dimensions`、`usage_notes`。

补丁中出现任何其他键（如 `id`、`baseline_score`、`last_score`、`edits`、`lifecycle`）→ 整个补丁被拒绝并返回非 0，不做静默丢弃。

## 退出码约定

| 码 | 含义 |
|----|------|
| `0` | 正常 |
| `1` | 业务失败：NOT FOUND / 非法输入 / 白名单拒绝 / `guard` 检出未闭环 |
| `2` | 步数超限硬中止 |
