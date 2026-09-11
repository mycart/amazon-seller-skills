# -*- coding: utf-8 -*-
"""
main.py
亚马逊多店铺多商城财务分析工具 · 命令行入口

用法：
    python main.py --input ./reports --output ./分析结果.xlsx

参数：
    --input   存放所有 MonthlySummary PDF 的文件夹（会自动扫描该文件夹下所有 .pdf）
    --output  生成的 Excel 分析报告路径（默认: ./亚马逊财务分析报告.xlsx）
    --config  可选，自定义语言关键词配置文件路径（默认使用同目录下 lang_config.json）
"""

import argparse
import sys
from pathlib import Path

from parser import parse_folder, load_lang_config
from report import build_excel_report


def main():
    ap = argparse.ArgumentParser(description="亚马逊多店铺多商城月度报告 · 财务分析工具")
    ap.add_argument("--input", "-i", required=True, help="存放 PDF 报告的文件夹路径")
    ap.add_argument("--output", "-o", default="亚马逊财务分析报告.xlsx", help="输出 Excel 文件路径")
    ap.add_argument("--config", "-c", default=None, help="自定义 lang_config.json 路径（可选）")
    args = ap.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"❌ 输入文件夹不存在: {input_dir}")
        sys.exit(1)

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ 在 {input_dir} 下没有找到任何 .pdf 文件")
        sys.exit(1)

    print(f"📂 找到 {len(pdf_files)} 个 PDF 文件，开始解析...")
    cfg = load_lang_config(args.config) if args.config else load_lang_config()
    records = parse_folder(str(input_dir), cfg)

    ok = [r for r in records if "error" not in r]
    bad = [r for r in records if "error" in r]

    for r in ok:
        flag = "✅"
        print(f"  {flag} {r['file']}  —  {r.get('shop')} / {r.get('country')}  "
              f"收入 {r.get('revenue')}  净利润 {r.get('net_profit'):.2f}")
    for r in bad:
        print(f"  ⚠️  解析失败: {r['file']}  —  {r['error']}")

    if not ok:
        print("❌ 没有任何文件解析成功，请检查 PDF 格式，或在 lang_config.json 中补充对应语言的关键词。")
        sys.exit(1)

    out_path = build_excel_report(records, args.output)
    print(f"\n✅ 分析报告已生成: {out_path}")
    print(f"   共 {len(ok)} 份商城报表，涉及店铺: {sorted(set(r.get('shop') for r in ok if r.get('shop')))}")


if __name__ == "__main__":
    main()
