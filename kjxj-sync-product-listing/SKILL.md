---
name: kjxj-sync-product-listing
description: "将 Listing 优化结果批量同步到 Amazon 多国家分类商品报告。支持多 ASIN、多国家分类报告匹配、执行前审核确认、绿色更新标记，并在输出副本中只保留已修改 ASIN 行及其关联父 ASIN 行。"
---

# KJXJ Sync Product Listing

用于把已审核的 Amazon Listing 优化结果同步到分类商品报告（`.xlsm` / `.xlsx`）。适用于多个 ASIN、多个国家站点和多个报告文件的批量处理。支持 US、CA、MX、BR、UK、DE、FR、IT、ES、NL、SE、PL、BE、JP、AU、IN、AE、SA、SG、TR、IE 的本地化模板字段。

## 输入优先级

1. 用户明确提供的 `listing-optimization-report-*.json`。
2. 当前对话中包含完整标题、商品亮点、描述、五点和后台词的 Listing 优化结果。
3. 用户明确提供的 Listing 审查报告 Markdown 或表格。

标准 JSON 是首选来源。缺少必要字段、站点码或 ASIN 时，记录为无法执行项，不得推测或编造内容。

## 固定流程

### 阶段 1：只读审核与计划

1. 收集所有优化报告，使用 `(marketplace, ASIN)` 作为唯一键。
2. 优先从用户提供的分类商品报告中匹配站点；用户未提供时，仅在用户明确指定的目录中递归查找候选 `.xlsm`、`.xlsx`、`.xls` 文件。
3. 识别分类报告站点时，按以下证据交叉确认：
   - 优化报告中的 `marketplace`。
   - 文件名中的国家、语言或站点代码。
   - 工作簿字段中的 `marketplace_id`、语言标签、站点专属字段和模板语言。
4. 只有站点证据一致时，才能建立 ASIN 到报告文件的匹配。多个同等候选、站点冲突、模板字段不完整、或找不到文件时，列为无法执行项。
5. 扫描模板第 3–5 行。优先以第 5 行 Amazon 属性 ID 定位标题、商品名称、商品亮点、描述、全部五点和后台词；本地化显示字段名作为兼容回退。隐藏列与可见列同等处理，重复 Bullet 字段按列顺序映射。
6. 从第 7 行起以 `ASIN + 产品标识类型` 匹配商品行。优化目标字段为空时仍属于可填充商品行；报价专用行不写入。
7. 站点必须由文件名、`marketplace_id`、模板语言三类证据中的至少两类交叉确认；优化报告中的 `IT`、`Amazon IT`、国家英文名和本地语言国家名会先归一化。冲突或无法唯一确认时阻塞。
8. 多个模板工作表时，仅在一个工作表命中全部目标 ASIN、产品 ID 类型匹配且 Listing 字段完整时自动选择；同分或部分命中时阻塞。
9. 默认优先短标题方案 1：标题、商品名称和商品亮点同步使用方案 1。可通过 `--title-option ASIN=方案号` 覆盖，或用 `--short-title-policy require-selection|long` 改变默认策略。

在写入前必须以中文输出简明方案，至少包含：

| 国家站 | ASIN | 站点证据 | 分类商品报告 | 工作表/行 | 更新字段/列/隐藏状态 | 标题模式 | 源字段状态 | 状态/阻塞原因 |
|---|---|---|---|---|---|---|---|

用户可以修改方案。只有用户明确回复“确认执行”“按此执行”等同义指令后，才能进入阶段 2。

### 阶段 2：批量执行

1. 对每份分类商品报告创建输出副本，绝不修改源文件。
2. 按 ASIN、报告文件和工作表分组更新所有已确认记录。
3. 仅更新优化报告明确提供的字段：`Title`、商品标题、商品亮点、产品描述、五点描述、后台搜索词。除用户通过计划明确跳过的字段外，空白目标单元格同样写入优化数据。
4. 每个实际写入的单元格填充浅绿色 `#C6EFCE`。
5. 品牌、材质、尺寸、颜色、图片、价格、库存、合规及其他未明确提供的字段保持原值。
6. 输出默认保存到当前项目的 `outputs/`；`--output-dir` 可覆盖默认路径，但不得指向源报告目录或其子目录。输出命名为 `YYYY-MM-DD_Amazon<国家站>_分类商品报告_Listing同步完成_<ASIN数量>ASIN_vN.<原扩展名>`，自动递增版本且不覆盖已有副本。
7. 选择短标题方案时，Title、商品名称和商品亮点同步使用该方案；未提供亮点方案时写入标准长标题，并保留模板中已有亮点。
8. 完成同一工作表的全部写入后，保持第 1–6 行（含第 6 行）原样不动；第 7 行起仅保留本次已修改的 ASIN 记录行及其直接关联的父 ASIN 行。整行删除其他数据，再按原有先后顺序将保留行连续排列到第 7、8、9 行，以此类推，不得留下空白间隔。优先通过 `Parent SKU -> SKU` 识别父行，同时兼容 `Parent ASIN -> Product ID`。

`.xlsm` / `.xlsx` 使用 OOXML 定点更新，仅改动命中的工作表部件与样式部件。`.xls` 仅做识别和计划；除非用户接受兼容转换输出，否则将其列为无法无损执行项。

### 阶段 3：验证与交付

对每个输出文件验证：

- 工作表列表和属性标题行与源文件一致；第 1–6 行内容、样式和行号不变。
- 更新单元格内容与优化报告一致，填充为 `#C6EFCE`。
- 第 7 行起只存在已修改 ASIN 行及其关联父 ASIN 行；其他数据行已整行删除，所有保留行从第 7 行开始连续排列且没有空白行。
- 父 ASIN 行、报价专用字段及不在字段映射内的保留内容不变。
- OOXML 压缩包可正常读取，且仅预期工作表与样式部件发生变化。
- 新建的空单元格节点按列顺序写入，避免 Excel 忽略内容。

最终提供每一个结果文件的绝对路径，并列出已更新 ASIN、更新行数、保留的父 ASIN 行数、删除的数据行数、写入单元格数和未处理项。

## 脚本

先运行只读预检：

```bash
python3 <skill>/scripts/listing_sync.py plan \
  --reports /path/report-1.json /path/report-2.json \
  --workbooks /path/DE-category.xlsm /path/US-category.xlsx \
  --title-option B0F596K897=1 \
  --output /path/listing-sync-plan.json
```

短标题策略示例：

```bash
python3 <skill>/scripts/listing_sync.py plan \
  --reports /path/any-valid-listing.json \
  --workbooks /path/IT-category.xlsm \
  --short-title-policy first \
  --output /path/listing-sync-plan.json
```

也可以通过用户已确认的目录找候选文件：

```bash
python3 <skill>/scripts/listing_sync.py plan \
  --reports-dir /path/reports \
  --workbooks-dir /path/category-reports \
  --output /path/listing-sync-plan.json
```

确认后执行：

```bash
python3 <skill>/scripts/listing_sync.py apply \
  --plan /path/listing-sync-plan.json
```

如用户明确要求某字段不填充，可在预检中声明：

```bash
python3 <skill>/scripts/listing_sync.py plan \
  --reports /path/report.json \
  --workbooks /path/category.xlsx \
  --skip-field B0EXAMPLE=description \
  --output /path/listing-sync-plan.json
```

## 失败边界

- 不搜索未被用户授权的目录。
- 不使用文件名或语言猜测站点后直接写入；站点证据冲突时停止该项。
- 不覆盖来源文件或已有输出文件。
- 不把输出副本写入源报告目录或其子目录。
- 不在用户未选择标题方案时写入多个标题方案中的任意一个。
- 不把优化建议、审核评分、核心卖点说明写入不存在对应属性的模板列。
