---
name: kjxj-sync-amz-inventory
description: "将用户提供的产品信息 Excel 中 Item Code 对应的可售库存同步到 Amazon 库存模板的 Template 工作表 Quantity 列。适用于两个本地 .xlsx/.xlsm 文件的库存更新、库存归零和 Amazon 模板副本生成；不下载文件、不更新价格、不发送邮件。"
---

# KJXJ Amazon 库存同步

把名称包含“产品信息”的源文件中的 `可售库存`，按 `Item Code` 子串匹配同步到 Amazon 目标模板。始终生成新副本，不覆盖源文件。

## 识别输入

1. 用户提供两个 Excel 文件时，文件名包含“产品信息”的文件是源文件，另一个是目标文件。
2. 如果没有且仅有一个文件名包含“产品信息”，停止并说明无法唯一识别，禁止猜测。
3. 仅支持 OOXML 工作簿 `.xlsx` 和 `.xlsm`。旧版 `.xls` 不执行无损写入。
4. 本技能仅处理本地文件，不使用浏览器、同步网站、Seller Central、邮件或价格更新流程。

## 固定规则

- 源工作簿中必须唯一找到一个工作表和同一表头行，同时包含精确字段 `Item Code` 与 `可售库存`。数据从表头下一行开始。
- 目标工作表优先使用名称严格为 `Template` 的表；否则可使用名称语义为“模板”的常见语言工作表。候选表必须通过结构校验：前 6 行 A 列存在 SKU 表头、C 列存在 Quantity 表头，数据从第 7 行开始。
- 如用户明确指定工作表，使用 `--sheet` 并仍执行结构校验。
- 从目标工作表第 7 行开始轮询 A 列 SKU。源 `Item Code` 去除首尾空白后，如原始字符完整存在于目标 SKU 中即为匹配；匹配区分大小写，不修改中间字符。
- 只有唯一源数据行匹配时才允许写入。多个 Item Code 或重复源数据行同时匹配时，跳过并报告，不得选择最长项或第一项。
- 唯一匹配且 `可售库存` 为有效数字时，将其写入同一目标行 C 列；数值小于等于 5 时写入数字 `0`。
- 无匹配、空库存、非数字库存和多重匹配行都保持目标原值不变。

## 执行流程

先运行只读预检：

```bash
python3 <skill-dir>/scripts/sync_inventory.py plan \
  --source /absolute/产品信息.xlsx \
  --target /absolute/amazon-template.xlsm
```

检查输出中的工作表、字段行、目标 SKU 数、唯一匹配、多重匹配、无效库存及预计写入值。预检无阻塞错误后执行：

```bash
python3 <skill-dir>/scripts/sync_inventory.py apply \
  --source /absolute/产品信息.xlsx \
  --target /absolute/amazon-template.xlsm
```

可选参数：

```bash
python3 <skill-dir>/scripts/sync_inventory.py apply \
  --source /absolute/产品信息.xlsx \
  --target /absolute/amazon-template.xlsm \
  --sheet Template \
  --output /absolute/result.xlsm
```

未指定 `--output` 时，在目标文件同目录生成 `<原文件名>_库存已更新.<扩展名>`；如已存在则递增 `_v2`、`_v3`。不得覆盖目标文件或已有结果。

## 完成标准

- 输出文件可作为 ZIP/OOXML 正常重新读取。
- 工作表列表、工作簿关系及非目标工作表部件保持不变。
- `.xlsm` 中存在的 VBA 和其他宏相关部件保持原始内容；原文件本身不含宏部件时不虚构宏。
- 仅唯一匹配且库存有效的目标行发生数量更新。
- 最终用中文报告输出绝对路径、更新行数、归零行数、未匹配行、多重匹配行和无效库存行。

## 失败边界

- 不覆盖任何输入文件。
- 不根据相似字段名猜测 `Item Code` 或 `可售库存`。
- 不在多个源工作表、多个目标工作表或多重 SKU 匹配之间静默选择。
- 不将缺失或错误库存转换为 0。
- 不修改价格、配送渠道、SKU、标题或其他模板字段。
