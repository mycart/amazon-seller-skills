# Amazon Seller Skills 团队使用说明

本文档说明当前仓库中已经共享的 Codex skills，以及团队成员如何安装、使用和同步这些技能。

## 仓库信息

- GitHub 仓库：`mycart/amazon-seller-skills`

## 当前已共享技能

- `ads-amazon2`
- `amazon-asin-availability-monitor2`
- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `amazon-product-research2`

## 安装方式

从 GitHub 单独安装某一个技能：

```bash
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-asin-availability-monitor2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-product-research2 -g
```

如果只需要其中一个 skill，只执行对应那一条命令即可。

## 技能适用场景

### `ads-amazon2`

简介：

- 用于深度审查 Amazon Ads 投放结构、搜索词收割、否词纪律、ACOS/TACOS 与基础 DSP 视角。

示例提示词：

```text
Use ads-amazon2 to audit my Amazon advertising account. I have Sponsored Products, Sponsored Brands, and Sponsored Display running. Review campaign structure, search-term harvesting, ACOS discipline, and brand analytics usage.
```

```text
Use ads-amazon2 to review my last 60 days of Amazon Ads reports and generate an Amazon Ads Health Score with a prioritized action plan.
```

### `amazon-asin-availability-monitor2`

简介：

- 用于在没有 SP-API 权限时，通过 Amazon 前台页面监控自有 ASIN 是否可购买，并在异常时通过邮件和飞书通知。

示例提示词：

```text
使用 amazon-asin-availability-monitor2，帮我创建 ASIN 可购买性监控模板。
```

```text
使用 amazon-asin-availability-monitor2，检查当前工作区的 config.yaml 和 Excel 清单是否配置正确。
```

### `amazon-listing-optimization2`

简介：

- 用于创建新 Listing、审计现有 Listing，并输出关键词覆盖、文案优化与标题/卖点方案。

示例提示词：

```text
Create a listing for a portable blender. Keywords: portable blender, smoothie maker, USB rechargeable, travel blender, personal blender. Material: BPA-free Tritan. Color: White. Capacity: 380ml. Tone: Friendly.
```

```text
Use amazon-listing-optimization2 to optimize ASIN B0XXXXXXX. Please output the full optimized listing, detailed audit report, title options, and Excel report.
```

### `amazon-ppc-campaign2`

简介：

- 用于从 0 搭建 Amazon PPC 结构，或基于现有广告数据做调价、迁移和否词优化。

示例提示词：

```text
I'm launching a portable blender on Amazon US. Price: $39.99. Product cost: $8, shipping: $3, Amazon fees: $7.50. Here are my keywords: portable blender, personal blender, smoothie maker. Build me a PPC campaign structure.
```

```text
My PPC ACoS is 58% and my target is 30%. I have 3 campaigns: Auto ($800/month, ACoS 67%), Manual Broad ($1,100, ACoS 48%), Manual Exact ($500, ACoS 33%). Product margin is 54%. Help me optimize.
```

### `amazon-product-research2`

简介：

- 用于做 Amazon 选品研究、需求判断、竞争强度分析、利润空间评估与进入门槛验证。

示例提示词：

```text
Research "wireless earbuds" as a product opportunity on Amazon
```

```text
Should I sell "phone cases" or "phone stands"? Compare both opportunities
```

## 后续同步流程

这个仓库已经内置同步脚本。后续本地某个 skill 内容有修改时，可以按下面方式同步。

同步单个技能：

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-skill.sh <skill-name> "/path/to/local/skill" "Sync <skill-name>"
```

同步当前全部共享 skill：

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-all-team-skills.sh
```

当前这个仓库对应的本地技能源路径如下：

- `ads-amazon2` -> `/Users/apple/.agents/skills/ads-amazon2`
- `amazon-asin-availability-monitor2` -> `/Users/apple/.agents/skills/amazon-asin-availability-monitor2`
- `amazon-listing-optimization2` -> `/Users/apple/.agents/skills/amazon-listing-optimization2`
- `amazon-ppc-campaign2` -> `/Users/apple/.agents/skills/amazon-ppc-campaign2`
- `amazon-product-research2` -> `/Users/apple/.agents/skills/amazon-product-research2`

## 团队建议

- 安装 skill 时优先按需安装，不必一次性全部安装。
- 修改共享 skill 前先确认本地源目录是否正确，避免改错副本。
- 完成修改后优先使用仓库内脚本同步，保持团队共享版本统一。
- 后续继续新增其它 skill 时，延续当前“一个仓库、多个技能文件夹”的方式即可。
