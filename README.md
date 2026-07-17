# Amazon Seller Skills

这个仓库用于集中维护团队共享的 Amazon 卖家相关 Codex skills，采用单仓库、多技能目录的方式管理。

## 当前技能

- `ads-amazon2`
- `amazon-asin-availability-monitor2`
- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `amazon-product-research2`
- `kjxj-sync-cloud-drive`
- `monitor-asin-sale-chrome`
- `monitor-amazon-listing-chrome`

## 安装示例

按需安装单个 skill：

```bash
npx skills add mycart/amazon-seller-skills --skill amazon-asin-availability-monitor2 -g
```

更多示例：

```bash
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-product-research2 -g
npx skills add mycart/amazon-seller-skills --skill kjxj-sync-cloud-drive -g
npx skills add mycart/amazon-seller-skills --skill monitor-asin-sale-chrome -g
npx skills add mycart/amazon-seller-skills --skill monitor-amazon-listing-chrome -g
```

## 团队使用说明

更完整的安装说明、适用场景、示例提示词和同步流程见 [TEAM-USAGE.md](TEAM-USAGE.md)。

## 同步命令

同步单个 skill：

```bash
scripts/sync-skill.sh <skill-name> /path/to/local/skill
```

同步当前全部共享 skill：

```bash
scripts/sync-all-team-skills.sh
```

后续同步统一在 `main` 分支执行并推送到 `origin/main`。如曾使用临时分支修改 skill，必须先合并到 `main`，确认 `main` 推送成功后删除本地和远端临时分支，避免技能版本分散在功能分支。
