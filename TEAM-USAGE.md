# Amazon Seller Skills 团队使用说明

本文档用于说明当前这个仓库里已经共享的 Codex Skills，以及团队成员如何安装、使用和同步这些技能。

## 仓库信息

- GitHub 仓库：`mycart/amazon-seller-skills`

## 当前已共享技能

- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `ads-amazon2`

## 安装方式

从 GitHub 单独安装某一个技能：

```bash
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
```

如果某位成员只需要其中一个技能，只执行对应那一条命令即可。

## 技能适用场景

### `amazon-listing-optimization2`

适合用于：

- 根据关键词创建全新的 Amazon Listing
- 审核和优化现有 Listing
- 生成 2026 年 7 月标题与商品亮点方案
- 导出 Listing 优化结果与审核信息到 Excel

示例提示词：

```text
Use amazon-listing-optimization2 to create an Amazon US listing for my portable blender. Brand: ACME. Keywords: portable blender, smoothie maker, USB rechargeable blender. Core selling points: USB-C charging, 380ml, BPA-free Tritan.
```

```text
Use amazon-listing-optimization2 to optimize ASIN B0XXXXXXX. Please output the full optimized listing, detailed audit report, July 2026 title options, and Excel report.
```

### `amazon-ppc-campaign2`

适合用于：

- 从 0 搭建 Amazon PPC 广告结构
- 审核现有 PPC 结构与 ACoS 表现
- 分析搜索词报告
- 输出调价建议与否词动作

示例提示词：

```text
Use amazon-ppc-campaign2 to build a launch PPC structure for my Amazon US product. Price: $39.99. Cost: $8. Shipping: $3. Amazon fees: $7.50. Keywords: portable blender, travel blender, smoothie maker.
```

```text
Use amazon-ppc-campaign2 to optimize my current PPC campaigns. Overall ACoS is 58%, target is 30%, and here is my search term report data.
```

### `ads-amazon2`

适合用于：

- 深度审查 Amazon Ads 账户
- 审核 Sponsored Products、Sponsored Brands、Sponsored Display，以及基础 DSP 情况
- 分析广告组合结构、否词纪律、TACOS 与品牌分析数据使用情况

说明：

- 这个技能更适合作为 Amazon Ads 审计/分析专家来使用
- 视 Codex 运行环境而定，它也可能在 Amazon Ads 或 Amazon PPC 场景下被自动触发，而不一定每次都需要手动点名调用

示例提示词：

```text
Use ads-amazon2 to audit my Amazon advertising account. I have Sponsored Products, Sponsored Brands, and Sponsored Display running. Review campaign structure, search-term harvesting, ACOS discipline, and brand analytics usage.
```

```text
Use ads-amazon2 to review my last 60 days of Amazon Ads reports and generate an Amazon Ads Health Score with a prioritized action plan.
```

## 后续同步流程

这个仓库已经内置了同步脚本。以后本地某个技能内容有修改后，可以使用以下方式同步。

同步单个技能：

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-skill.sh amazon-ppc-campaign2 "/Users/apple/.agents/skills/amazon-ppc-campaign2" "Sync amazon-ppc-campaign2"
```

该同步脚本会先执行 `git pull --rebase origin main`，然后把本地技能目录复制到仓库中，自动提交并推送回 GitHub。这样在后续团队多人维护时会更稳一些。

同步当前全部已共享团队技能：

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-all-team-skills.sh
```

当前这个仓库对应的本地技能源路径如下：

- `amazon-listing-optimization2` -> `/Users/apple/Documents/Listing优化建议/.agents/skills/amazon-listing-optimization2`
- `amazon-ppc-campaign2` -> `/Users/apple/.agents/skills/amazon-ppc-campaign2`
- `ads-amazon2` -> `/Users/apple/.codex/skills/ads-amazon2`

## 团队建议

- 安装技能时，优先按需安装，不必一次性全部安装。
- 修改共享技能前，先确认本地源目录是否正确，避免改错副本。
- 完成修改后，优先使用仓库内脚本同步，保持团队共享版本统一。
- 如果后续仓库中继续新增其它 skill，延续当前“一个仓库、多个技能文件夹”的方式即可，团队管理会更清晰。
