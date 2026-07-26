# Workflow Memory Schema

Store workflow memory in `state/workflows.json` with this shape:

```json
{
  "schema_version": 1,
  "updated_at": "2026-07-26T00:00:00+00:00",
  "workflows": [
    {
      "id": "keyword-mining",
      "name": "关键词挖掘",
      "aliases": ["关键词挖掘数据", "keyword mining"],
      "version": 1,
      "entry_url": "",
      "menu_path": ["工具", "关键词挖掘"],
      "marketplace": {
        "parameter": "marketplace",
        "default": "德国站",
        "control": {"role": "combobox", "label": "站点"}
      },
      "parameter_schema": {
        "keyword": {"label": "关键词", "required": true, "control": {"role": "textbox"}},
        "relevance_min": {"label": "相关度最小值", "required": false, "control": {"section": "相关度", "position": "min"}},
        "monthly_search_volume_min": {"label": "月搜索量最小值", "required": false, "control": {"section": "月搜索量", "position": "min"}}
      },
      "defaults": {
        "keyword": "hundebett",
        "relevance_min": 30,
        "monthly_search_volume_min": 1
      },
      "steps": [
        {"action": "select", "target": "marketplace"},
        {"action": "fill", "target": "keyword"},
        {"action": "click", "target": "立即查询"},
        {"action": "fill", "target": "relevance_min"},
        {"action": "fill", "target": "monthly_search_volume_min"},
        {"action": "click", "target": "开始筛选"},
        {"action": "click", "target": "导出"}
      ],
      "export_source": "关键词挖掘",
      "last_successful_at": "2026-07-26T00:00:00+00:00",
      "source_run": "/absolute/run/directory"
    }
  ]
}
```

## Rules

- Keep `id`, `name`, `defaults`, `parameter_schema`, `steps`, and `export_source` for every workflow.
- Use lowercase ASCII kebab-case for `id`.
- Keep aliases unique across workflows after trimming whitespace and case folding.
- Store semantic labels and stable attributes, not transient DOM node IDs or positional selectors.
- Reject keys containing `password`, `secret`, `token`, `cookie`, `local_storage`, `session_storage`, or `dom_snapshot` at any depth.
- Record or upgrade a workflow only when its source run contains at least one validated download.
- Increment `version` when replacing an existing workflow ID. Preserve the previous version if the new run fails.
