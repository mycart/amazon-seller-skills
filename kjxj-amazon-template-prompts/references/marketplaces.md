# 欧美市场规则

| 站点 | 国家/地区 | Amazon 域名 | 页面语言 | 目标货币 | 尺寸输出 |
|---|---|---|---|---|---|
| US | 美国 | amazon.com | en-US | USD | inch + cm |
| CA | 加拿大 | amazon.ca | en-CA/fr-CA | CAD | inch + cm |
| MX | 墨西哥 | amazon.com.mx | es-MX | MXN | cm |
| UK | 英国 | amazon.co.uk | en-GB | GBP | cm |
| DE | 德国 | amazon.de | de-DE | EUR | cm |
| FR | 法国 | amazon.fr | fr-FR | EUR | cm |
| IT | 意大利 | amazon.it | it-IT | EUR | cm |
| ES | 西班牙 | amazon.es | es-ES | EUR | cm |
| NL | 荷兰 | amazon.nl | nl-NL | EUR | cm |
| SE | 瑞典 | amazon.se | sv-SE | SEK | cm |
| PL | 波兰 | amazon.pl | pl-PL | PLN | cm |
| BE | 比利时 | amazon.com.be | nl-BE/fr-BE | EUR | cm |
| TR | 土耳其 | amazon.com.tr | tr-TR | TRY | cm |

## 内容本地化

- 保留用户模板中的字段标签、编号、缩进和下游 Skill 调用指令；仅本地化字段值及模板中面向市场的自然语言内容。
- 每个目标站以表中的页面语言本地化产品类型、核心关键词、材质、产品事实/卖点、变体颜色与尺寸，以及售价、成本和日预算。产品类型是产品核心关键词的同义语义字段，必须从目标站实时搜索页、自动补全、商品页标题或竞品标题取得证据。
- 加拿大默认 `en-CA`；若实时页面或用户指定法语，则使用 `fr-CA`。比利时默认 `nl-BE`；若实时页面明确为法语，则使用 `fr-BE`。不得混合两种语言的字段值。
- 美国使用英制并保留公制，加拿大使用双单位；其他站点使用公制。未验证的变体仅保留源模板的变体值，不推断其在目标站可售。
- 把产品页不可售、验证码、搜索失败、竞品来源类型、汇率来源、采集时间和失败原因写在模板代码块外的中文分析说明中，不得写进可复制模板正文。

## 取证最小记录

每个站点保存：`captured_at`、目标 URL、最终 URL、HTTP/浏览器状态、主 ASIN/变体 ASIN 状态、可见标题、关键词查询、自然竞品、Sponsored 补足、失败原因、汇率来源 URL、汇率值和原始币种。

`verified` 仅表示目标站页面满足域名、ASIN、非挑战和可见非空标题；`pending` 表示无法实时确认。`unavailable`、`challenge`、`failed` 均不得当作已验证。
