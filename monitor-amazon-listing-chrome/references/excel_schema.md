# Excel Schema

Workspace-first input:

```text
./ASIN可购买性监控模板.xlsx
```

If the workspace Excel is missing, the skill copies the legacy Excel when available, otherwise creates a fresh template.

Legacy default input:

```text
/Users/apple/Documents/Listing优化建议/ASIN可购买性监控模板.xlsx
```

Default sheet:

```text
ASIN监控清单
```

Required columns:

- `店铺名称`
- `ASIN值`
- `多站点简写（将多个站点写到一起通过标点符号分开多个站点）`

Optional columns:

- `卖家ID（可选）`
- `备注`

Site split separators:

```text
, ， ; ； 、 / whitespace newline
```

Supported sites:

```text
US, CA, MX, UK, DE, FR, IT, ES, NL, BE, JP, AU, IN
```

Rows are expanded into one target per `ASIN + site` and deduplicated by that pair.
