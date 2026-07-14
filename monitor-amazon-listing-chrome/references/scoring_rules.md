# Scoring Rules

Use a 100-point model:

- Title: 15
- Bullet Points: 15
- Images: 15
- A+ Content: 10
- Description: 10
- Pricing: 10
- Reviews: 15
- SEO / category / public attribute signals: 10

Score interpretation:

- `90-100`: Listing质量较好，低优先级优化
- `75-89`: 有优化空间，中优先级优化
- `60-74`: 明显不完善，高优先级优化
- `0-59`: 严重不完善，优先处理
- `无法审查`: 页面异常、访问受阻或数据不足

Do not score from stale cache or guessed values. If the page cannot be reviewed normally, keep identifying fields and status, then write `无法审查`.

Optimization recommendations must be operations-facing and specific to detected missing/weak fields. Do not generate a full rewritten listing unless the user explicitly asks for copywriting.

Report layout:

- First column: `备注`, copied from the user's input Excel and used as the Chinese product identifier.
- Column 2: `Listing完整度和质量评分`.
- Column 3: `页面状态`.
- Column 8: `核心优化建议`.
- Keep decision columns near the front: `Listing是否建议优化`, `Listing优化优先级`, `主要问题/缺失`.
- Keep ASIN, country, URL, page status, store, seller ID, concise dimension reviews, collection time, and screenshot path.
- Do not output separate repetitive columns for good points, shortcomings, missing parts, and recommendations in the Excel report; keep those details merged into `主要问题/缺失` and `核心优化建议`.
