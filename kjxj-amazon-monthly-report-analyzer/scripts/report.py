# -*- coding: utf-8 -*-
"""
report.py
把 parser.py 解析出的多份报告记录：
  1) 汇总成 DataFrame（跨币种统一折算为 EUR 用于汇总对比，原始币种数值仍保留）
  2) 按「店铺」「国家」维度汇总
  3) 自动生成「经营分析结论」：关键数字对比表 / 核心结论 / 经营建议 / 整体建议
  4) 输出为一份全中文表头的 Excel 分析报告（含图表、异常预警高亮）
"""

from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule

# Use a CJK-capable system font so Chinese sheet labels render consistently.
FONT_NAME = "PingFang SC"
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=11)
TITLE_FONT = Font(name=FONT_NAME, bold=True, size=14, color="1F4E78")
SECTION_FONT = Font(name=FONT_NAME, bold=True, size=12, color="1F4E78")
NORMAL_FONT = Font(name=FONT_NAME, size=10)
BOLD_FONT = Font(name=FONT_NAME, bold=True, size=10)
WARN_FILL = PatternFill("solid", fgColor="FFC7CE")
GOOD_FILL = PatternFill("solid", fgColor="C6EFCE")
NOTE_FONT = Font(name=FONT_NAME, size=9, italic=True, color="808080")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

MONEY_FMT = '#,##0.00;[RED]-#,##0.00'
PCT_FMT = '0.0%'

# ---------------------------------------------------------------------------
# 英文字段名 -> 中文表头
# ---------------------------------------------------------------------------
COLUMN_LABELS = {
    "shop": "店铺",
    "country": "商城(国家)",
    "period_year": "年份",
    "period_month": "月份",
    "currency": "原始币种",
    "fx_rate_to_eur": "折算汇率(→EUR)",
    "revenue": "收入(原币)",
    "expenses": "支出(原币)",
    "tax": "税费(原币)",
    "transfers": "转账(原币)",
    "net_profit": "净利润(原币)",
    "net_margin": "净利率",
    "ad_spend": "广告费(原币)",
    "acos": "ACOS(广告占收入比)",
    "revenue_eur": "收入(折EUR)",
    "expenses_eur": "支出(折EUR)",
    "net_profit_eur": "净利润(折EUR)",
    "ad_spend_eur": "广告费(折EUR)",
    "net_margin_eur": "净利率",
    "acos_eur": "ACOS(广告占收入比)",
    "metric_fba_selling_fees": "FBA销售费用",
    "metric_fba_transaction_fees": "FBA交易费",
    "metric_storage_fees": "仓储物流费",
    "metric_promotional_rebates": "促销折扣净额",
    "metric_refunds_fba": "FBA退款",
    "metric_service_fees": "服务费",
    "metric_liquidation_fees": "清算费用",
    "display_name": "店铺显示名",
    "legal_name": "法人主体(店铺唯一标识)",
    "period_start": "账期开始",
    "period_end": "账期结束",
    "file": "源文件",
    "marketplace_count": "覆盖商城数",
}


def _cn(df: pd.DataFrame) -> pd.DataFrame:
    """把 DataFrame 的列名整体转成中文（用于最终写入 Excel 前调用）。"""
    return df.rename(columns={c: COLUMN_LABELS.get(c, c) for c in df.columns})


def records_to_dataframe(records: list) -> pd.DataFrame:
    good = [r for r in records if "error" not in r]
    df = pd.DataFrame(good)
    if df.empty:
        return df
    cols_order = [
        "shop", "country", "period_year", "period_month", "currency", "fx_rate_to_eur",
        "revenue", "expenses", "tax", "transfers", "net_profit", "net_margin",
        "ad_spend", "acos",
        "revenue_eur", "expenses_eur", "net_profit_eur", "ad_spend_eur",
        "metric_fba_selling_fees", "metric_fba_transaction_fees",
        "metric_storage_fees", "metric_promotional_rebates",
        "metric_refunds_fba", "metric_service_fees", "metric_liquidation_fees",
        "display_name", "legal_name", "period_start", "period_end", "file",
    ]
    cols_order = [c for c in cols_order if c in df.columns]
    return df[cols_order]


def _aggregate(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """按 shop 或 country 维度汇总，统一用折算成 EUR 后的数值相加，避免跨币种直接相加出错。"""
    if df.empty:
        return df
    sum_cols = ["revenue_eur", "expenses_eur", "net_profit_eur", "ad_spend_eur"]
    sum_cols = [c for c in sum_cols if c in df.columns]
    grouped = df.groupby(by, dropna=False)[sum_cols].sum().reset_index()
    grouped["net_margin_eur"] = grouped.apply(
        lambda r: (r["net_profit_eur"] / r["revenue_eur"]) if r["revenue_eur"] else None, axis=1
    )
    grouped["acos_eur"] = grouped.apply(
        lambda r: (abs(r["ad_spend_eur"]) / r["revenue_eur"]) if r["revenue_eur"] else None, axis=1
    )
    other_dim = "country" if by == "shop" else "shop"
    grouped["marketplace_count"] = df.groupby(by)[other_dim].nunique().values
    return grouped.sort_values("net_profit_eur", ascending=False)


def aggregate_by_shop(df: pd.DataFrame) -> pd.DataFrame:
    return _aggregate(df, "shop")


def aggregate_by_country(df: pd.DataFrame) -> pd.DataFrame:
    return _aggregate(df, "country")


# ---------------------------------------------------------------------------
# Excel 样式辅助函数
# ---------------------------------------------------------------------------

def _style_header_row(ws, row_idx, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row_idx, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER


def _autofit(ws, df, start_col=1):
    for j, h in enumerate(df.columns, start=start_col):
        col_letter = get_column_letter(j)
        max_len = max([len(str(h))] + [len(str(v)) for v in df[h].astype(str)])
        ws.column_dimensions[col_letter].width = min(max(12, max_len + 2), 42)


def _apply_number_formats(ws, df, start_row, money_col_positions, pct_col_positions):
    n = len(df)
    for pos in money_col_positions:
        for i in range(start_row + 1, start_row + 1 + n):
            ws.cell(row=i, column=pos).number_format = MONEY_FMT
    for pos in pct_col_positions:
        for i in range(start_row + 1, start_row + 1 + n):
            ws.cell(row=i, column=pos).number_format = PCT_FMT


def _money_pct_positions(df, money_cols, pct_cols):
    cols = list(df.columns)
    money_pos = [i + 1 for i, c in enumerate(cols) if c in money_cols]
    pct_pos = [i + 1 for i, c in enumerate(cols) if c in pct_cols]
    return money_pos, pct_pos


def _add_conditional_formatting(ws, col_letter, first_row, last_row):
    rng = f"{col_letter}{first_row}:{col_letter}{last_row}"
    ws.conditional_formatting.add(
        rng, CellIsRule(operator="lessThan", formula=["0"], fill=WARN_FILL)
    )
    ws.conditional_formatting.add(
        rng, CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=GOOD_FILL)
    )


def _add_bar_chart(ws, title, cats_ref, data_ref, anchor):
    chart = BarChart()
    chart.type = "col"
    chart.title = title
    chart.y_axis.title = "EUR"
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.height = 8
    chart.width = 18
    ws.add_chart(chart, anchor)


def _write_df(ws, df_cn, start_row, money_col_positions=None, pct_col_positions=None):
    """写入一个已经是中文表头的 DataFrame，返回下一个可用行号。"""
    money_col_positions = money_col_positions or []
    pct_col_positions = pct_col_positions or []
    headers = list(df_cn.columns)
    for j, h in enumerate(headers, start=1):
        ws.cell(row=start_row, column=j, value=str(h))
    _style_header_row(ws, start_row, len(headers))

    for i, (_, row) in enumerate(df_cn.iterrows(), start=start_row + 1):
        for j, h in enumerate(headers, start=1):
            val = row[h]
            if pd.isna(val):
                val = None
            cell = ws.cell(row=i, column=j, value=val)
            cell.font = NORMAL_FONT
            cell.border = BORDER
            if j in money_col_positions and isinstance(val, (int, float)):
                cell.number_format = MONEY_FMT
            if j in pct_col_positions and isinstance(val, (int, float)):
                cell.number_format = PCT_FMT

    _autofit(ws, df_cn)
    return start_row + len(df_cn) + 1


def _write_text_block(ws, start_row, lines, col_span=8):
    """把一段中文文字（列表）按行写入，自动换行，返回下一个可用行号。"""
    row = start_row
    for line in lines:
        cell = ws.cell(row=row, column=1, value=line)
        cell.font = NORMAL_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_span)
        ws.row_dimensions[row].height = 18
        row += 1
    return row + 1


# ---------------------------------------------------------------------------
# 结论文字自动生成
# ---------------------------------------------------------------------------

def _fmt_eur(x):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.2f} EUR"


def _fmt_pct(x):
    if x is None or pd.isna(x):
        return "—"
    return f"{x*100:.1f}%"


def generate_conclusions(df: pd.DataFrame, by_shop: pd.DataFrame, by_country: pd.DataFrame):
    """
    生成结构化的中文经营分析结论，返回一个 dict：
      key_numbers_df : 关键数字对比表（DataFrame，中文列名，已按净利润排序）
      key_conclusions: 核心结论（字符串列表）
      recommendations: 经营建议（字符串列表，按店铺/商城给出具体建议）
      overall_advice  : 整体建议（字符串列表）
    """
    lines_conclusions = []
    lines_reco = []
    lines_overall = []

    if df.empty:
        return {
            "key_numbers_df": pd.DataFrame(),
            "key_conclusions": ["本次没有解析到任何有效数据。"],
            "recommendations": [],
            "overall_advice": [],
        }

    # 单个商城维度也需要 EUR 口径的净利率/ACOS（汇总表里已经有，这里按商城逐行补充）
    df = df.copy()
    df["net_margin_eur"] = df.apply(
        lambda r: (r["net_profit_eur"] / r["revenue_eur"]) if r["revenue_eur"] else None, axis=1
    )
    df["acos_eur"] = df.apply(
        lambda r: (abs(r["ad_spend_eur"]) / r["revenue_eur"]) if r["revenue_eur"] else None, axis=1
    )

    total_rev = df["revenue_eur"].sum()
    total_exp = df["expenses_eur"].sum()
    total_net = df["net_profit_eur"].sum()
    total_ad = df["ad_spend_eur"].sum()
    overall_margin = (total_net / total_rev) if total_rev else None
    overall_acos = (abs(total_ad) / total_rev) if total_rev else None

    n_shops = df["shop"].nunique()
    n_markets = len(df)
    n_countries = df["country"].nunique()

    # ---------- 核心结论 ----------
    lines_conclusions.append(
        f"【整体规模】本期共汇总 {n_shops} 个店铺、{n_countries} 个国家/商城、{n_markets} 份商城报表"
        f"（不同币种已按参考汇率统一折算为 EUR 用于汇总比较，原始币种数值见「明细-按商城」表）。"
    )
    lines_conclusions.append(
        f"【整体盈亏】全部店铺合计：收入 {_fmt_eur(total_rev)}，支出 {_fmt_eur(total_exp)}，"
        f"净利润 {_fmt_eur(total_net)}，综合净利率 {_fmt_pct(overall_margin)}，"
        f"综合广告占比(ACOS) {_fmt_pct(overall_acos)}。"
    )

    loss_shops = pd.DataFrame()
    if not by_shop.empty:
        best_shop = by_shop.iloc[0]
        worst_shop = by_shop.iloc[-1]
        lines_conclusions.append(
            f"【表现最好的店铺】{best_shop['shop']}：净利润 {_fmt_eur(best_shop['net_profit_eur'])}，"
            f"净利率 {_fmt_pct(best_shop['net_margin_eur'])}，覆盖 {int(best_shop['marketplace_count'])} 个商城。"
        )
        if worst_shop["shop"] != best_shop["shop"]:
            flag = "亏损" if worst_shop["net_profit_eur"] < 0 else "净利润最低"
            lines_conclusions.append(
                f"【表现最弱的店铺】{worst_shop['shop']}：净利润 {_fmt_eur(worst_shop['net_profit_eur'])}"
                f"（{flag}），净利率 {_fmt_pct(worst_shop['net_margin_eur'])}。"
            )

        loss_shops = by_shop[by_shop["net_profit_eur"] < 0]
        if not loss_shops.empty:
            names = "、".join(loss_shops["shop"].tolist())
            lines_conclusions.append(f"【亏损店铺】以下店铺本期整体为亏损状态，需要重点关注：{names}。")
        else:
            lines_conclusions.append("【亏损店铺】本期没有店铺整体层面出现亏损。")

    if not by_country.empty:
        best_country = by_country.iloc[0]
        worst_country = by_country.iloc[-1]
        lines_conclusions.append(
            f"【表现最好的商城】{best_country['country']}：净利润合计 {_fmt_eur(best_country['net_profit_eur'])}，"
            f"净利率 {_fmt_pct(best_country['net_margin_eur'])}。"
        )
        if worst_country["country"] != best_country["country"]:
            lines_conclusions.append(
                f"【表现最弱的商城】{worst_country['country']}：净利润合计 {_fmt_eur(worst_country['net_profit_eur'])}，"
                f"净利率 {_fmt_pct(worst_country['net_margin_eur'])}。"
            )

    # 单个商城维度的异常点（亏损 / 高ACOS / 低利润率）
    loss_rows = df[df["net_profit_eur"] < 0].sort_values("net_profit_eur")
    high_acos_rows = df[(df["acos_eur"].notna()) & (df["acos_eur"] > 0.5)].sort_values("acos_eur", ascending=False)
    low_margin_rows = df[(df["net_margin_eur"].notna()) & (df["net_margin_eur"] >= 0) &
                          (df["net_margin_eur"] < 0.05) & (df["revenue_eur"] > 0)]

    if not loss_rows.empty:
        worst = loss_rows.iloc[0]
        lines_conclusions.append(
            f"【最严重的单一商城亏损】{worst['shop']}-{worst['country']}：净利润 {_fmt_eur(worst['net_profit_eur'])}。"
        )
    if not high_acos_rows.empty:
        worst_ad = high_acos_rows.iloc[0]
        lines_conclusions.append(
            f"【广告效率最差的商城】{worst_ad['shop']}-{worst_ad['country']}：ACOS 高达 {_fmt_pct(worst_ad['acos_eur'])}"
            f"（广告花费占该商城收入的比例），是本期最需要优先处理的广告问题。"
        )

    # ---------- 经营建议（按店铺/商城给出具体行动） ----------
    if not loss_rows.empty:
        lines_reco.append("【亏损商城 · 优先止血】")
        for _, r in loss_rows.iterrows():
            reason = []
            if r.get("acos_eur") and r["acos_eur"] > 0.5:
                reason.append(f"ACOS高达{_fmt_pct(r['acos_eur'])}")
            if r.get("metric_promotional_rebates") and r["revenue"] and r["metric_promotional_rebates"] < -0.15 * r["revenue"]:
                reason.append("促销折扣力度偏大")
            reason_txt = "，主要原因：" + "、".join(reason) if reason else ""
            lines_reco.append(
                f"  - {r['shop']}-{r['country']}：净利润 {_fmt_eur(r['net_profit_eur'])}{reason_txt}。"
                f"建议立即核查广告活动ACOS、退款/退货原因，必要时暂停高花费低转化的广告组。"
            )

    high_acos_not_loss = high_acos_rows[~high_acos_rows.index.isin(loss_rows.index)]
    if not high_acos_not_loss.empty:
        lines_reco.append("【广告效率偏低（暂未亏损，但需要预警）】")
        for _, r in high_acos_not_loss.iterrows():
            lines_reco.append(
                f"  - {r['shop']}-{r['country']}：ACOS {_fmt_pct(r['acos_eur'])}，"
                f"建议复核广告关键词匹配方式和出价，排查是否存在无效点击或竞价过高。"
            )

    if not low_margin_rows.empty:
        lines_reco.append("【净利率偏低，接近盈亏平衡】")
        for _, r in low_margin_rows.iterrows():
            lines_reco.append(
                f"  - {r['shop']}-{r['country']}：净利率仅 {_fmt_pct(r['net_margin_eur'])}，"
                f"建议关注FBA费用、促销折扣和退款率，寻找降本空间。"
            )

    healthy_rows = df[(df["net_margin_eur"].notna()) & (df["net_margin_eur"] >= 0.3) &
                       (df["ad_spend_eur"] == 0)]
    if not healthy_rows.empty:
        lines_reco.append("【健康且尚未投广告的商城 · 可考虑测试放量】")
        for _, r in healthy_rows.iterrows():
            lines_reco.append(
                f"  - {r['shop']}-{r['country']}：净利率 {_fmt_pct(r['net_margin_eur'])}，本期零广告投入，"
                f"说明自然流量基础较好，可小额测试广告（如净利润的10-15%）验证放量的投入产出比。"
            )

    if not lines_reco:
        lines_reco.append("本期各店铺/商城均未触发明显的经营预警，继续保持监控即可。")

    # ---------- 整体建议 ----------
    lines_overall.append(
        "1. 把「广告费占收入比(ACOS)」和「净利率」作为每月必看的两个核心指标，"
        "建议设定预警阈值（如 ACOS>50%、净利率<5%），超过阈值的商城当月内就要复核，不要等到月底汇总才发现。"
    )
    if not loss_shops.empty:
        lines_overall.append(
            f"2. 优先集中资源处理亏损店铺（{'、'.join(loss_shops['shop'].tolist())}），"
            f"在止血之前不建议对这些店铺加大广告投入或铺新品。"
        )
    else:
        lines_overall.append("2. 当前没有店铺整体亏损，可以把重心放在「优化高ACOS商城」和「复制表现好的商城打法」上。")
    if not by_shop.empty:
        lines_overall.append(
            f"3. 可以把表现最好的店铺「{by_shop.iloc[0]['shop']}」的选品/定价/促销打法，"
            f"复制到表现较弱的店铺或商城，做同店铺跨国对比、同商城跨店铺对比，找出差异点。"
        )
    lines_overall.append(
        "4. 本报告的跨币种汇总使用的是生成报告当天的参考汇率（非报告当期的真实汇率），"
        "仅用于经营分析和店铺间横向比较，如需用于正式财务/税务用途，请替换为对应账期的真实汇率。"
    )
    lines_overall.append(
        "5. 建议每月固定用本工具重新生成一次报告，跟踪「亏损店铺」「高ACOS商城」名单的变化趋势，"
        "而不仅仅看单月快照。"
    )

    key_numbers_df = by_shop.copy()
    if not key_numbers_df.empty:
        key_numbers_df = key_numbers_df[[
            "shop", "marketplace_count", "revenue_eur", "expenses_eur",
            "net_profit_eur", "net_margin_eur", "ad_spend_eur", "acos_eur"
        ]]

    return {
        "key_numbers_df": key_numbers_df,
        "key_conclusions": lines_conclusions,
        "recommendations": lines_reco,
        "overall_advice": lines_overall,
    }


# ---------------------------------------------------------------------------
# 主入口：生成 Excel
# ---------------------------------------------------------------------------

def build_excel_report(records: list, output_path: str):
    df = records_to_dataframe(records)
    if df.empty:
        raise ValueError("没有可用的解析结果，请检查输入的 PDF 是否为亚马逊月度报告摘要。")

    by_shop = aggregate_by_shop(df)
    by_country = aggregate_by_country(df)
    conclusions = generate_conclusions(df, by_shop, by_country)

    money_cols_en = {"revenue", "expenses", "tax", "transfers", "net_profit", "ad_spend",
                      "revenue_eur", "expenses_eur", "net_profit_eur", "ad_spend_eur",
                      "metric_fba_selling_fees", "metric_fba_transaction_fees",
                      "metric_storage_fees", "metric_promotional_rebates",
                      "metric_refunds_fba", "metric_service_fees", "metric_liquidation_fees"}
    pct_cols_en = {"net_margin", "acos", "net_margin_eur", "acos_eur"}

    df_money_pos, df_pct_pos = _money_pct_positions(df, money_cols_en, pct_cols_en)
    shop_money_pos, shop_pct_pos = _money_pct_positions(by_shop, money_cols_en, pct_cols_en) if not by_shop.empty else ([], [])
    country_money_pos, country_pct_pos = _money_pct_positions(by_country, money_cols_en, pct_cols_en) if not by_country.empty else ([], [])
    key_money_pos, key_pct_pos = _money_pct_positions(
        conclusions["key_numbers_df"], money_cols_en, pct_cols_en
    ) if not conclusions["key_numbers_df"].empty else ([], [])

    df_cn = _cn(df)
    by_shop_cn = _cn(by_shop)
    by_country_cn = _cn(by_country)
    key_numbers_cn = _cn(conclusions["key_numbers_df"])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame().to_excel(writer, sheet_name="经营分析结论", index=False)
        df_cn.to_excel(writer, sheet_name="明细-按商城", index=False, startrow=2)
        by_shop_cn.to_excel(writer, sheet_name="汇总-按店铺", index=False, startrow=2)
        by_country_cn.to_excel(writer, sheet_name="汇总-按国家", index=False, startrow=2)

        wb = writer.book

        # =================== 经营分析结论（放在第一个 sheet） ===================
        ws0 = wb["经营分析结论"]
        ws0["A1"] = "亚马逊多店铺多商城 · 经营分析结论"
        ws0["A1"].font = TITLE_FONT
        row = 3

        ws0.cell(row=row, column=1, value="一、关键数字对比表（按店铺汇总，已统一折算为 EUR）").font = SECTION_FONT
        row += 1
        if not key_numbers_cn.empty:
            table_start = row
            row = _write_df(ws0, key_numbers_cn, row, key_money_pos, key_pct_pos)
            profit_col_name = COLUMN_LABELS["net_profit_eur"]
            if profit_col_name in key_numbers_cn.columns:
                profit_col = list(key_numbers_cn.columns).index(profit_col_name) + 1
                first_data_row = table_start + 1
                last_data_row = table_start + len(key_numbers_cn)
                _add_conditional_formatting(ws0, get_column_letter(profit_col), first_data_row, last_data_row)
        else:
            ws0.cell(row=row, column=1, value="无数据")
            row += 2

        ws0.cell(row=row, column=1, value="二、核心结论").font = SECTION_FONT
        row += 1
        row = _write_text_block(ws0, row, conclusions["key_conclusions"])

        ws0.cell(row=row, column=1, value="三、经营建议（按店铺/商城）").font = SECTION_FONT
        row += 1
        row = _write_text_block(ws0, row, conclusions["recommendations"])

        ws0.cell(row=row, column=1, value="四、整体建议").font = SECTION_FONT
        row += 1
        row = _write_text_block(ws0, row, conclusions["overall_advice"])

        ws0.cell(row=row, column=1,
                 value="注：本表所有 EUR 折算金额均使用生成报告当天的参考汇率，仅用于经营分析对比，非正式财务/报税数据。").font = NOTE_FONT
        ws0.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
        ws0.column_dimensions["A"].width = 110
        ws0.sheet_view.showGridLines = False

        # =================== 明细 sheet ===================
        ws = wb["明细-按商城"]
        ws["A1"] = "亚马逊多店铺多商城 · 财务明细（原始币种）"
        ws["A1"].font = TITLE_FONT
        _style_header_row(ws, 3, len(df_cn.columns))
        _apply_number_formats(ws, df_cn, 3, df_money_pos, df_pct_pos)
        _autofit(ws, df_cn)
        if "net_profit_eur" in df.columns:
            col_idx = list(df.columns).index("net_profit_eur") + 1
            col_letter = get_column_letter(col_idx)
            _add_conditional_formatting(ws, col_letter, 4, 3 + len(df))
        ws.freeze_panes = "A4"

        # =================== 按店铺汇总 sheet ===================
        ws2 = wb["汇总-按店铺"]
        ws2["A1"] = "按店铺汇总（跨国相加，统一折算为 EUR）"
        ws2["A1"].font = TITLE_FONT
        _style_header_row(ws2, 3, len(by_shop_cn.columns))
        _apply_number_formats(ws2, by_shop_cn, 3, shop_money_pos, shop_pct_pos)
        _autofit(ws2, by_shop_cn)
        if "net_profit_eur" in by_shop.columns and not by_shop.empty:
            col_idx = list(by_shop.columns).index("net_profit_eur") + 1
            col_letter = get_column_letter(col_idx)
            _add_conditional_formatting(ws2, col_letter, 4, 3 + len(by_shop))
        ws2.freeze_panes = "A4"

        if len(by_shop) > 0:
            n = len(by_shop)
            shop_col = list(by_shop.columns).index("shop") + 1
            rev_col = list(by_shop.columns).index("revenue_eur") + 1
            profit_col = list(by_shop.columns).index("net_profit_eur") + 1
            cats_ref = Reference(ws2, min_col=shop_col, min_row=4, max_row=3 + n)
            data_ref = Reference(ws2, min_col=rev_col, max_col=profit_col, min_row=3, max_row=3 + n)
            _add_bar_chart(ws2, "各店铺 收入 / 支出 / 净利润 (EUR)", cats_ref, data_ref, f"A{6 + n}")

        # =================== 按国家汇总 sheet ===================
        ws3 = wb["汇总-按国家"]
        ws3["A1"] = "按国家（商城）汇总（跨店铺相加，统一折算为 EUR）"
        ws3["A1"].font = TITLE_FONT
        _style_header_row(ws3, 3, len(by_country_cn.columns))
        _apply_number_formats(ws3, by_country_cn, 3, country_money_pos, country_pct_pos)
        _autofit(ws3, by_country_cn)
        if "net_profit_eur" in by_country.columns and not by_country.empty:
            col_idx = list(by_country.columns).index("net_profit_eur") + 1
            col_letter = get_column_letter(col_idx)
            _add_conditional_formatting(ws3, col_letter, 4, 3 + len(by_country))
        ws3.freeze_panes = "A4"

        if len(by_country) > 0:
            n = len(by_country)
            country_col = list(by_country.columns).index("country") + 1
            rev_col = list(by_country.columns).index("revenue_eur") + 1
            profit_col = list(by_country.columns).index("net_profit_eur") + 1
            cats_ref = Reference(ws3, min_col=country_col, min_row=4, max_row=3 + n)
            data_ref = Reference(ws3, min_col=rev_col, max_col=profit_col, min_row=3, max_row=3 + n)
            _add_bar_chart(ws3, "各国商城 收入 / 支出 / 净利润 (EUR)", cats_ref, data_ref, f"A{6 + n}")

        # =================== 经营预警 sheet ===================
        ws4 = wb.create_sheet("经营预警")
        ws4["A1"] = "经营预警（自动生成，供参考）"
        ws4["A1"].font = TITLE_FONT
        alerts = []
        for _, r in df.iterrows():
            label = f"{r.get('shop', '')} - {r.get('country', '')}"
            if r.get("net_profit_eur") is not None and r["net_profit_eur"] < 0:
                alerts.append([label, "亏损", f"净利润 {r['net_profit_eur']:.2f} EUR（折算），本月该商城为亏损状态"])
            if r.get("acos_eur") is not None and r["acos_eur"] and r["acos_eur"] > 0.5:
                alerts.append([label, "广告效率过低", f"ACOS 高达 {r['acos_eur']*100:.1f}%，广告花费占销售额比例过高，需要立即复核广告活动"])
            if r.get("net_margin_eur") is not None and 0 <= r["net_margin_eur"] < 0.05 and (r.get("revenue_eur") or 0) > 0:
                alerts.append([label, "利润率偏低", f"净利率仅 {r['net_margin_eur']*100:.1f}%，接近盈亏平衡，需要关注成本结构"])
        alert_df = pd.DataFrame(alerts, columns=["店铺-商城", "预警类型", "说明"]) if alerts else \
            pd.DataFrame([["-", "-", "本期无触发预警的商城"]], columns=["店铺-商城", "预警类型", "说明"])
        _write_df(ws4, alert_df, 3)

        # 调整 sheet 顺序，结论页放最前
        wb.move_sheet("经营分析结论", offset=-(len(wb.sheetnames) - 1))

    return output_path
