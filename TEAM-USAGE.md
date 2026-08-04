# Amazon Seller Skills 团队使用说明

本文档用于说明当前这个仓库里已经共享的 Codex Skills，以及团队成员如何安装、使用和同步这些技能。

## 仓库信息

- GitHub 仓库：`mycart/amazon-seller-skills`

## 当前已共享技能

- `ads-amazon2`
- `amazon-asin-availability-monitor2`
- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `amazon-product-research2`
- `kjxj-export-ss-data`
- `kjxj-optimize-sync-listing`
- `kjxj-sync-cloud-drive`
- `kjxj-sync-product-listing`
- `monitor-amazon-listing-chrome`
- `monitor-asin-sale-chrome`

## 安装方式

从 GitHub 单独安装某一个技能：

```bash
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-asin-availability-monitor2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-product-research2 -g
npx skills add mycart/amazon-seller-skills --skill kjxj-export-ss-data -g
npx skills add mycart/amazon-seller-skills --skill kjxj-optimize-sync-listing -g
npx skills add mycart/amazon-seller-skills --skill kjxj-sync-cloud-drive -g
npx skills add mycart/amazon-seller-skills --skill kjxj-sync-product-listing -g
npx skills add mycart/amazon-seller-skills --skill monitor-amazon-listing-chrome -g
npx skills add mycart/amazon-seller-skills --skill monitor-asin-sale-chrome -g
```

如果某位成员只需要其中一个技能，只执行对应那一条命令即可。

## 技能适用场景

### `ads-amazon2`

简介：

- Amazon Ads deep analysis covering Sponsored Products, Sponsored Brands (incl.

示例提示词：

```text
Amazon Ads Health Score: XX/100 (Grade: X)

Campaign Structure:     XX/100  ████████░░  (15%)
Search-Term Harvesting: XX/100  ██████████  (25%)
ACOS / TACOS Discipline:XX/100  █████████░  (20%)
Bid & Budget Mgmt:      XX/100  ████████░░  (15%)
Sponsored Brands:       XX/100  ███████░░░  (10%)
Sponsored Display:      XX/100  ███████░░░  (10%)
Brand Analytics:        XX/100  █████░░░░░  (5%)
```

### `amazon-asin-availability-monitor2`

简介：

- Monitor Amazon ASIN front-end buyability for seller-owned listings without SP-API access.

示例提示词：

```text
使用 amazon-asin-availability-monitor2，帮我创建 ASIN 可购买性监控模板。
```

```text
使用 amazon-asin-availability-monitor2，检查当前工作区的 config.yaml 和 Excel 清单是否配置正确。
```

### `amazon-listing-optimization2`

简介：

- Create and optimize Amazon listings in 13 marketplaces using product facts, keywords, competitor listings, optional CSV/XLSX keyword files, and seller-provided core selling points.

示例提示词：

```text
npx skills add nexscope-ai/Amazon-Skills --skill amazon-listing-optimization -g
```

```text
Create a listing for a portable blender. Keywords: portable blender, smoothie maker, USB rechargeable, travel blender, personal blender. Material: BPA-free Tritan. Color: White. Capacity: 380ml. Tone: Friendly.
```

### `amazon-ppc-campaign2`

简介：

- Amazon PPC campaign builder and optimizer for sellers.

示例提示词：

```text
npx skills add nexscope-ai/Amazon-Skills --skill amazon-ppc -g
```

```text
I'm launching a portable blender on Amazon US. Price: $39.99. Product cost: $8, shipping: $3, Amazon fees: $7.50. Here are my keywords: portable blender, personal blender, smoothie maker. Build me a PPC campaign structure.
```

### `amazon-product-research2`

简介：

- Comprehensive product research and opportunity analysis for Amazon sellers.

示例提示词：

```text
npx skills add nexscope-ai/Amazon-Skills --skill amazon-product-research2 -g
```

```text
Research "wireless earbuds" as a product opportunity on Amazon
```

### `kjxj-export-ss-data`

简介：

- Automate SellerSprite Amazon data exports in a persistent Chrome Profile, including login, tool and marketplace selection, filtering, export-job polling, local download collection,

示例提示词：

```text
python3 <skill-dir>/scripts/export_support.py preflight --workspace <workspace>
```

```text
python3 <skill-dir>/scripts/export_support.py resolve-workflow \
  --tool "关键词挖掘" --marketplace "德国站" \
  --params-json '{"keyword":"hundebett","relevance_min":30,"monthly_search_volume_min":1}'
```

### `kjxj-optimize-sync-listing`

简介：

- 端到端编排 Amazon Listing 优化、关键词准备、2026 短标题与商品亮点、分类商品报告预检和确认后写入、主 ASIN PPC 广告方案及 Rufus/Alexa 商品 Q/A。用于用户提供主 ASIN、站点、核心关键词、卖点、可选竞品和变体、可选 CSV/XLSX 关键词资料、XLSM 分类商品报告及可选广告参数，并要求先完整审核五份 Mark

示例提示词：

```text
## 阻塞说明
- 阶段：<当前阶段与受影响 ASIN/文件>
- 原因：<可验证的报错、缺失字段或限制；不猜测>
- 已尝试：<按时间顺序列出路径及结果>
- 解决方法：<用户现在需要完成的最小操作，或可由系统继续执行的下一步>
- 下次预防：<上传、权限、页面可访问性、文件格式或数据准备建议>
- 继续条件：<满足后从哪个阶段恢复>
```

```text
使用 $kjxj-optimize-sync-listing 执行 Amazon Listing 优化、分类报告同步与主ASIN广告方案创建。

1. 目标ASIN与站点
   主ASIN：[填写，例如 B0F4NDR1ZB]
   Amazon站点：[填写，例如 UK、DE、IE]

2. 核心关键词
   [填写；多个关键词可用逗号、顿号或换行分隔]

3. 竞品ASIN（选填，最多3个）
   [填写；没有则写“无”]

4. 产品核心卖点（支持中文）
   [填写；多个卖点可用顿号或换行分隔]

5. 变体信息（选填，每行一个）
   [变体ASIN]-[颜色]-[尺寸或型号]([补充说明])
   示例：B0F596K897-灰色-M(适合中型猫咪)
   [没有变体则写“无”]

6. 关键词资料（选填；均不选择时自动使用 Amazon autocomplete 补词）
   使用上传文件：[是/否]
   使用卖家精灵自动挖掘：[是/否]
   关键词文件：[选择上传文件时，上传一个或多个 CSV/XLSX；否则写“无”]

7. 分类商品报告
   [上传一个与目标站点一致的 XLSM 文件]

8. 主ASIN广告方案参数（均可选）
   月度广告预算：[选填；EUR/USD站未填默认600，其它站按执行当天汇率将USD 600换算为本币]
   财务依据：[选填；未填完整成本或盈亏平衡ACoS时，默认盈亏平衡ACoS为40%]
   A. 单件到岸成本：[选填]；Amazon单件费用：[选填；两项完整时优先使用]
   B. 盈亏平衡ACoS：[选填百分比]
   预期转化率：[选填；不知道则写“未知”]
   商品阶段：[新品/成熟期；默认新品]
```

### `kjxj-sync-cloud-drive`

简介：

- 将用户指定文件或零碎文本智能整理并同步到跨境电商云盘，含目录归类、长期资源索引维护、文本台账、冲突判断、图片/PDF 压缩和月度操作日志。Use when the user asks to sync, copy, archive, update, overwrite, append, classify, or store files/text in the

示例提示词：

```text
python3 <skill-dir>/scripts/check_sync_item.py --source "/absolute/source" --target "/absolute/target" --hash
```

### `kjxj-sync-product-listing`

简介：

- 将 Listing 优化结果批量同步到 Amazon 多国家分类商品报告。支持多 ASIN、多国家分类报告匹配、执行前审核确认、绿色更新标记，并在输出副本中只保留已修改 ASIN 行及其关联父 ASIN 行。

示例提示词：

```text
python3 <skill>/scripts/listing_sync.py plan \
  --reports /path/report-1.json /path/report-2.json \
  --workbooks /path/DE-category.xlsm /path/US-category.xlsx \
  --title-option B0F596K897=1 \
  --output /path/listing-sync-plan.json
```

```text
python3 <skill>/scripts/listing_sync.py plan \
  --reports /path/any-valid-listing.json \
  --workbooks /path/IT-category.xlsm \
  --short-title-policy first \
  --output /path/listing-sync-plan.json
```

### `monitor-amazon-listing-chrome`

简介：

- Monitor Amazon ASIN listing completeness and quality across multiple marketplaces using the Codex Chrome plugin, a configurable Excel ASIN list, local scoring/report scripts, and o

示例提示词：

```text
/Users/apple/Documents/Listing优化建议/amazon_chrome_listing_monitor/config.yaml
```

```text
/Users/apple/Documents/Listing优化建议/ASIN可购买性监控模板.xlsx
```

### `monitor-asin-sale-chrome`

简介：

- Monitor Amazon ASIN front-end sale/buyability status with the Codex Chrome plugin instead of launching standalone Playwright.

示例提示词：

```text
使用 monitor-asin-sale-chrome，帮我创建 ASIN 销售状态监控模板。
```

```text
使用 monitor-asin-sale-chrome，检查当前工作区的 config.yaml 和 Excel 清单是否配置正确。
```

## 后续同步流程

这个仓库已经内置了同步脚本。以后本地某个技能内容有修改后，可以使用以下方式同步。

同步单个技能：

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-skill.sh <skill-name> "/path/to/local/skill" "Sync <skill-name>"
```

同步当前全部已共享团队技能：

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-all-team-skills.sh
```

当前这个仓库对应的本地技能源路径如下：

- `ads-amazon2` -> `/Users/apple/.agents/skills/ads-amazon2`
- `amazon-asin-availability-monitor2` -> `/Users/apple/.agents/skills/amazon-asin-availability-monitor2`
- `amazon-listing-optimization2` -> `/Users/apple/.codex/skills/amazon-listing-optimization2`
- `amazon-ppc-campaign2` -> `/Users/apple/.agents/skills/amazon-ppc-campaign2`
- `amazon-product-research2` -> `/Users/apple/.agents/skills/amazon-product-research2`
- `kjxj-export-ss-data` -> `/Users/apple/.codex/skills/kjxj-export-ss-data`
- `kjxj-optimize-sync-listing` -> `/Users/apple/.agents/skills/kjxj-optimize-sync-listing`
- `kjxj-sync-cloud-drive` -> `/Users/apple/.agents/skills/kjxj-sync-cloud-drive`
- `kjxj-sync-product-listing` -> `/Users/apple/.codex/skills/kjxj-sync-product-listing`
- `monitor-amazon-listing-chrome` -> `/Users/apple/.codex/skills/monitor-amazon-listing-chrome`
- `monitor-asin-sale-chrome` -> `/Users/apple/.codex/skills/monitor-asin-sale-chrome`

## 团队建议

- 安装技能时，优先按需安装，不必一次性全部安装。
- 修改共享技能前，先确认本地源目录是否正确，避免改错副本。
- 完成修改后，优先使用仓库内脚本同步，保持团队共享版本统一。
- 如果后续仓库中继续新增其它 skill，延续当前“一个仓库、多个技能文件夹”的方式即可，团队管理会更清晰。
