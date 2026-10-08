#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SMBU-CA 招新报名数据清洗与统计工具

子命令（随需求迭代逐步加入）：
    overview   需求1：读入 CSV 并打印概览（行数 / 各列空值 / 完全重复行）

用法示例：
    python recruit_tool.py overview --input data/raw/2026-recruit-signup.csv

环境：Python 3.8+，仅标准库，无需安装第三方包。
"""
import argparse
import csv
import sys
from collections import OrderedDict

# CSV 必需的列名（顺序即问卷导出顺序）
REQUIRED_COLUMNS = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]


# ---------------------------------------------------------------------------
# 通用：读入 CSV
# ---------------------------------------------------------------------------
def load_csv(path):
    """读入问卷导出的 CSV，返回 (rows, row_numbers)。

    - 使用 utf-8-sig 编码，兼容带 BOM 和不带 BOM 的 UTF-8 文件。
    - 每个字段自动去除首尾空白（问卷导出常含多余空格）。
    - row_numbers[i] 为该数据行在原文件中的行号（表头为第 1 行，数据从第 2 行起）。
    - 若缺少必需列，直接报错退出。
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise SystemExit(
                "错误：CSV 缺少必需列 %r；实际列名为 %r" % (missing, header)
            )
        rows, row_numbers = [], []
        for line_no, raw in enumerate(reader, start=2):
            row = {c: (raw.get(c) or "").strip() for c in REQUIRED_COLUMNS}
            rows.append(row)
            row_numbers.append(line_no)
    return rows, row_numbers


# ---------------------------------------------------------------------------
# 需求1：概览
# ---------------------------------------------------------------------------
def overview_summary(rows, row_numbers):
    """计算概览信息，返回字典：
    {
      "total": 数据行数,
      "nulls": {列名: 空值数},
      "dup_groups": [(完整行键, [出现行号...]), ...],  # 仅含出现 >1 次的组
    }
    """
    total = len(rows)
    nulls = OrderedDict((c, sum(1 for r in rows if not r[c])) for c in REQUIRED_COLUMNS)

    seen = OrderedDict()
    for i, r in enumerate(rows):
        key = tuple(r[c] for c in REQUIRED_COLUMNS)
        seen.setdefault(key, []).append(row_numbers[i])
    dup_groups = [(k, nums) for k, nums in seen.items() if len(nums) > 1]
    return {"total": total, "nulls": nulls, "dup_groups": dup_groups}


def cmd_overview(args):
    rows, row_numbers = load_csv(args.input)
    info = overview_summary(rows, row_numbers)
    print("=" * 60)
    print("报名数据概览")
    print("=" * 60)
    print("数据文件：%s" % args.input)
    print("数据行数（不含表头）：%d 行" % info["total"])
    print()
    print("每列空值统计：")
    for c, n in info["nulls"].items():
        print("  %-6s : %d 个空值" % (c, n))
    print()
    dups = info["dup_groups"]
    if dups:
        print("完全重复的行：共 %d 组（涉及 %d 行）" % (
            len(dups), sum(len(nums) for _, nums in dups)))
        for gi, (key, nums) in enumerate(dups, 1):
            # 显示该组首行的姓名/学号便于人工定位
            r = {c: v for c, v in zip(REQUIRED_COLUMNS, key)}
            print("  第 %d 组：出现 %d 次（文件行 %s）姓名=%r 学号=%r"
                  % (gi, len(nums), "、".join(str(n) for n in nums),
                     r["姓名"], r["学号"]))
        print("  （完全重复行会在需求2的「问题清单」中标记为「重复报名」）")
    else:
        print("完全重复的行：无")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="recruit_tool.py",
        description="SMBU-CA 招新报名数据清洗与统计工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("overview", help="需求1：读入 CSV 并打印概览")
    p.add_argument("--input", required=True, help="报名表 CSV 文件路径")
    p.set_defaults(func=cmd_overview)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
