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
import os
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
# 需求2：校验与清洗
# ---------------------------------------------------------------------------
# 问题原因标签
REASON_ID_MISSING = "学号缺失"
REASON_ID_NOT_DIGIT = "学号非纯数字"
REASON_EMAIL_MISSING = "邮箱缺失"
REASON_EMAIL_MISMATCH = "邮箱与学号不匹配"
REASON_DUP_IDENTICAL = "重复报名（完全重复，已保留首条）"
REASON_DUP_CONFLICT = "重复报名（信息不一致，需人工确认）"

# 问题清单的列
PROBLEM_COLUMNS = ["行号", "姓名", "学号", "邮箱", "问题原因"]


def validate_rows(rows, row_numbers):
    """对全部行做校验，返回 (clean, problems)。

    - clean: [(row_no, row_dict), ...]  通过校验、可进入干净数据的行
    - problems: [{"行号":.., "姓名":.., "学号":.., "邮箱":.., "问题原因":"原因1；原因2"}, ...]

    校验规则：
    1) 学号必须非空且为纯数字；
    2) 学号有效时，邮箱必须等于「学号@smbu.edu.cn」（大小写不敏感）；
    3) 同一学号出现多次视为重复报名——
       完全相同的多行保留首条、其余进问题清单；
       学号相同但内容不同的全部进问题清单（需人工确认）。
    """
    # 按学号分组（空学号不参与重复判断）
    id_groups = {}
    for i, r in enumerate(rows):
        sid = r["学号"]
        if sid:
            id_groups.setdefault(sid, []).append(i)

    problems = {}  # idx -> list[str]

    for i, r in enumerate(rows):
        sid = r["学号"]
        reasons = []

        # —— 学号校验 ——
        if not sid:
            reasons.append(REASON_ID_MISSING)
        elif not sid.isdigit():
            reasons.append(REASON_ID_NOT_DIGIT)
        else:
            # —— 邮箱校验（仅学号有效时）——
            expected = sid + "@smbu.edu.cn"
            email = r["邮箱"]
            if not email:
                reasons.append(REASON_EMAIL_MISSING)
            elif email.lower() != expected.lower():
                reasons.append(REASON_EMAIL_MISMATCH)

        # —— 重复报名校验 ——
        if sid and len(id_groups[sid]) > 1:
            members = id_groups[sid]
            first = rows[members[0]]
            all_identical = all(rows[j] == first for j in members)
            if all_identical:
                # 完全重复：保留首条，其余标记
                if i != members[0]:
                    reasons.append(REASON_DUP_IDENTICAL)
            else:
                # 信息不一致：全部标记
                reasons.append(REASON_DUP_CONFLICT)

        if reasons:
            problems[i] = reasons

    clean = [(row_numbers[i], rows[i]) for i in range(len(rows)) if i not in problems]
    problem_list = [
        {
            "行号": row_numbers[i],
            "姓名": rows[i]["姓名"],
            "学号": rows[i]["学号"],
            "邮箱": rows[i]["邮箱"],
            "问题原因": "；".join(reasons),
        }
        for i, reasons in sorted(problems.items())
    ]
    return clean, problem_list


def write_csv_rows(path, columns, records):
    """把记录列表写入 CSV（UTF-8 with BOM，Excel 友好）。"""
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for rec in records:
            w.writerow(rec)


def cmd_validate(args):
    rows, row_numbers = load_csv(args.input)
    clean, problems = validate_rows(rows, row_numbers)

    out_path = os.path.join(args.outdir, "问题清单.csv")
    write_csv_rows(out_path, PROBLEM_COLUMNS, problems)

    print("=" * 60)
    print("校验与清洗")
    print("=" * 60)
    print("数据文件：%s" % args.input)
    print("原始行数：%d 行" % len(rows))
    print("问题行数：%d 行" % len(problems))
    print("清洗后剩余：%d 行" % len(clean))
    print()

    # 按原因分类统计
    reason_count = {}
    for p in problems:
        for r in p["问题原因"].split("；"):
            reason_count[r] = reason_count.get(r, 0) + 1
    if reason_count:
        print("问题原因分布（一行可能有多个原因）：")
        for reason, n in sorted(reason_count.items(), key=lambda x: -x[1]):
            print("  %s：%d 行" % (reason, n))
    print()
    print("问题清单已导出 -> %s" % out_path)
    print("（原文件未被修改，问题行单独列出并注明原因，供人工核实）")
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

    p = sub.add_parser("validate", help="需求2：校验与清洗，导出问题清单")
    p.add_argument("--input", required=True, help="报名表 CSV 文件路径")
    p.add_argument("--outdir", default="data/output", help="输出目录（默认 data/output）")
    p.set_defaults(func=cmd_validate)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
