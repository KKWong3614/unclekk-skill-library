# skill-library 条目结构（skill_library.json）

库是单个 JSON 文件，顶层：

```json
{
  "entries": { "sl_001": { ...条目... } },
  "meta": { "created": "ISO时间", "version": 1 }
}
```

## 单条技能条目字段

| 字段 | 含义 |
|------|------|
| `id` | 自动生成，如 `sl_001` |
| `task_type` | 任务类型键，如 `competitive_report` |
| `description` | 这条技能解决什么任务 |
| `approach` | 可复用的拆解方式 / Roadmap（核心沉淀物） |
| `key_dimensions` | 关键分析维度数组 |
| `tags` | 检索标签数组 |
| `baseline_score` | 上次「被接受的改动」对应的验证分（棘轮基线） |
| `last_score` | 最近一次记录的使用分 |
| `edits` | 被接受的改动历史 [{at, patch, score}] |
| `created` / `updated` | ISO 时间戳 |

## 三阶段工作流

1. **capture（沉淀）**：完成任务后 `add`，把拆解方式 + 关键维度存库。
2. **retrieve（复用）**：新任务前 `find`，复用命中条目的 `approach`，只补缺口。
3. **optimize（自优化）**：复用后 `record` 打分；`optimize` 提改动，仅当新分 **严格大于** `baseline_score` 才接受，否则回滚。

## 棘轮纪律

`optimize` 的接受条件是 `new_score > baseline_score`（严格大于）。
等于或更低 → 拒绝并回滚，保证技能分数随时间单调不降。
这与论文 SkillOpt 的「仅当严格提升才接受编辑」一致。
