# Amazon Seller Skills

这个仓库用于集中维护团队共享的 Amazon 卖家相关 Codex skills，采用单仓库、多技能目录的方式管理。

## 当前技能

- `ads-amazon2`
- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `amazon-product-research2`

## 安装示例

按需安装单个 skill：

```bash
npx skills add mycart/amazon-seller-skills --skill amazon-product-research2 -g
```

更多示例：

```bash
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
```

## 团队使用说明

更完整的安装说明、适用场景、示例提示词和同步流程见 [TEAM-USAGE.md](/Users/apple/Documents/amazon-seller-skills/TEAM-USAGE.md)。

## 同步命令

同步单个 skill：

```bash
scripts/sync-skill.sh <skill-name> /path/to/local/skill
```

同步当前全部共享 skill：

```bash
scripts/sync-all-team-skills.sh
```
