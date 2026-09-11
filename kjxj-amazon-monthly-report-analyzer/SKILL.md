---
name: kjxj-amazon-monthly-report-analyzer
description: Parses Amazon Seller Central "Monthly Summary"/"月度报告摘要" PDF statements (any marketplace language — French, German, Dutch, English, Swedish, etc. — any currency) into a Chinese-language Excel workbook with per-marketplace detail, shop-level and country-level roll-ups (auto-converted to a common currency), auto-generated business conclusions/recommendations, and an anomaly-alert sheet (losses, high ACOS, thin margins). Use whenever the user uploads or references Amazon "月度报告摘要"/"MonthlySummary" PDFs, asks to analyze/汇总/对比 Amazon store or marketplace financials, asks about 店铺经营情况/ACOS/广告费占比, or wants a cross-shop/cross-country/cross-currency roll-up of Amazon seller activity — even with just one file, or no explicit request for Excel. Also use to add support for a new marketplace language/currency.
---

# Amazon 月度报告摘要 · 财务分析工具

把亚马逊卖家后台导出的《月度报告摘要》PDF（Seller Central → Reports → Date Range Reports →
Generate Statement，各商城语言不同：法语/德语/荷兰语/英语/瑞典语等，币种也不同：EUR/USD/SEK等）
解析成结构化数据，并生成一份**全中文表头**的 Excel 分析报告，包含：

- 明细-按商城（每个 PDF 一行，原始币种）
- 汇总-按店铺（同一店铺跨国相加，已统一折算成 EUR）
- 汇总-按国家（同一商城跨店铺相加，已统一折算成 EUR）
- 经营分析结论（关键数字对比表 / 核心结论 / 经营建议 / 整体建议，自动生成）
- 经营预警（亏损、ACOS 过高、净利率偏低）

## 何时使用本技能

- 用户上传了任意数量的亚马逊 "MonthlySummary" / "月度报告摘要" / "Monthly Summary" PDF，
  哪怕只有 1 份，也应该使用本技能来解析，而不是手动读 PDF 文本。
- 用户要求"分析""汇总""对比"亚马逊店铺/商城的财务数据、经营状况、ACOS、广告费占比等。
- 用户提到多个店铺（同一法人主体在不同国家开店，或不同法人主体的多个店铺）需要按店铺维度汇总。
- 用户要求把分析结果输出成 Excel。
- 用户要求给这个工作流新增一种语言/国家的支持。

## 前置条件

运行环境需要能执行 Python（bash + python3）。首次使用前安装依赖（多次调用无需重复安装，
可以先 `python3 -c "import pdfplumber, pandas, openpyxl"` 探测是否已装好）：

```bash
pip install -r scripts/requirements.txt --break-system-packages
```
（如果环境的 pip 不需要 `--break-system-packages` 参数，去掉即可；报错了再加。）

## 标准工作流

1. **收集 PDF**：把用户提供的所有月度报告 PDF 放到同一个文件夹（如果是聊天上传的文件，
   通常已经在磁盘某个上传目录里，直接把这些文件复制或直接指向该目录即可，不需要手动挪动
   到别的地方，除非路径里混有不相关的 PDF）。

2. **文件命名**：`main.py` 会从文件名解析"店铺"和"国家"，期望格式：
   `{店铺名}-{国家}-{任意年月标记}MonthlySummary.pdf`
   例如 `跨界馨家-法国-2026AugMonthlySummary.pdf`。这正是亚马逊后台默认导出的命名习惯，
   通常不需要用户手动改名。如果文件名不是这个格式，工具仍会尝试解析财务数字本身
   （四大总计的提取不依赖文件名，也不依赖语言），只是"店铺""国家"字段可能是 None，
   之后可以在生成的 Excel 明细表里提示用户手动补充。

3. **运行分析脚本**：

   ```bash
   python3 scripts/main.py --input <PDF所在文件夹> --output <输出xlsx路径>
   ```

   终端会打印每个文件解析出的店铺/国家/收入/净利润，方便快速核对是否解析正确。
   如果某个文件解析失败，终端会打印 `⚠️ 解析失败`，此时不要静默忽略——检查该 PDF
   是否真的是"月度报告摘要"格式（而非交易明细/库存报告等其他类型的报表）。

4. **核对关键数字**：抽查 1-2 份 PDF，对照终端打印或 Excel「明细-按商城」sheet 里的
   收入/支出/税费/转账四个总计，确认与 PDF 上「Résumés/Zusammenfassungen/Summaries/...」
   小节里的数字一致。四大总计的提取逻辑与语言无关（利用报告固定版式），出错概率很低；
   容易出问题的是`广告费`等细分科目（依赖 `lang_config.json` 里的关键词匹配），
   如果某个语言的广告费之类字段没提取到（Excel 里显示为空），参考下面"新增语言"章节处理。

5. **把生成的 Excel 呈现给用户**（如果所在环境有文件展示/下载机制，用它展示；
   同时可以在对话里用 1-2 句话概括「经营分析结论」sheet 里的核心结论，不需要把整个
   Excel 内容逐字复述一遍，Excel 本身已经包含完整的结论和建议）。

## 新增一种语言/商城（不用改代码）

`scripts/lang_config.json` 是唯一需要维护的配置文件，包含几类内容：

- `section_headers`：收入/支出/税费/转账 四个分类标题在各语言下的写法
  （用于定位明细区块，不是必须的——四大总计提取不依赖这个，但明细科目提取依赖它来避免
  误匹配"汇总小节里的描述性文字"）。
- `total_column_markers` / `subtotal_markers`：报表里"总计/Totaux/Gesamt/Totals/..."
  和"小计/sous-totaux/Zwischensummen/..."的各语言写法。
- `display_name_labels` / `legal_name_labels`：报表表头"显示名称""法人实体名称"的各语言写法。
- `country_name_map`：中文国家名 → 英文（目前只用于展示，非必须）。
- `currency_symbol_map`：有些语言的报表不写标准三字母货币代码（如瑞典语写 "kr"），
  用这个表做补充识别。
- `key_metrics`：广告费/FBA销售费/FBA交易费/仓储费/促销折扣/FBA退款/服务费/清算费用
  在各语言下的具体写法（可能同一语言不同商城/国家措辞还略有差异，比如法国和比利时的
  法语报表用词不完全一样，需要分别列出）。
- `exchange_rates_to_eur`：把各币种折算成 EUR 用于跨国/跨店铺汇总的参考汇率。
  **这是近似值**，如果用户需要更准确的汇总，应该更新成对应账期的实际汇率。

新增语言时，打开这个 JSON，在对应分类的数组里，把亚马逊该语言报表里实际显示的文字加进去，
不需要动 `parser.py` 或 `report.py` 里的任何代码。如果不确定某个语言的具体写法，
可以先跑一次 `scripts/main.py`，看看哪些 `metric_*` 字段在 Excel 明细表里是空的，
再针对性地去查那份 PDF 里对应行的原文（可以用 `pdfplumber` 打印该 PDF 的
`page.extract_text(layout=True)` 来看，参考 `scripts/parser.py` 里 `_extract_key_metrics`
函数的实现方式）。

## 常见问题排查

- **报错 `ModuleNotFoundError: No module named 'pdfplumber'`**：先执行
  `pip install -r scripts/requirements.txt --break-system-packages`。
- **某份 PDF 解析后收入/支出对不上**：大概率是版式和已支持的语言差异较大
  （比如报告不是标准的"月度报告摘要"，而是"交易明细报表"等其他类型），
  先确认 PDF 类型，再考虑是否需要扩展 `lang_config.json`。
- **多币种汇总的数字感觉不对**：检查 `lang_config.json` 里 `exchange_rates_to_eur`
  的汇率是否是最新的，工具默认使用生成分析时抓取的近似汇率，不是报告当期的历史汇率。
- **想要用欧元以外的币种做汇总基准**：目前 `parser.py`/`report.py` 里硬编码汇总基准
  是 EUR（`revenue_eur` 等字段名），如果要换成其他基准币种，把
  `exchange_rates_to_eur` 的含义改成"换算到目标币种"，并把相关字段改名即可，
  逻辑本身与具体基准币种无关。
