# -*- coding: utf-8 -*-
"""生成模拟招新报名数据，用于演示和测试招新数据清洗工具。

固定随机种子（2026），保证多次运行结果一致、可复现。
运行后输出：data/raw/2026-recruit-signup.csv（UTF-8 with BOM，模拟问卷导出格式）。

刻意埋入的问题行（在 README 假设下）：
- 学号非纯数字若干行（含字母、尾随字母）
- 学号为空若干行
- 学号纯数字但位数为 11 位（工具不校验位数 → 视为正常，验证假设）
- 学号尾随空格（工具自动去空白 → 视为正常，验证假设）
- 邮箱与学号不匹配若干行（qq/gmail、邮箱数字≠学号、邮箱为空）
- 邮箱大写域名（工具大小写不敏感 → 视为正常，验证假设）
- 完全重复行 3 组（问卷重复提交）
- 同一学号但信息不同 2 组（重复报名且需人工判断）
- 姓名空若干行、志愿1 空若干行、志愿2 空（只填一个志愿）若干行
"""
import csv
import os
import random

random.seed(2026)

COLS = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]

SURNAMES = list("张王李赵刘陈杨黄周吴徐孙马朱胡郭何高林郑梁谢宋唐许韩")
GIVEN1 = list("伟强磊军勇杰涛明超秀娟霞平刚桂英华慧文建志永世丽芳玉")
GIVEN2 = list("健坤鹏程欣怡思远佳豪睿宁悦琳晗梓辰")
DEPTS = ["技术部", "宣传部", "学术部", "外联部", "综合行政部"]
REFERRERS = ["", "", "", "张伟", "李娜", "王强", "刘洋", "陈静", "赵磊", "孙悦", "周航",
             "段茗尧", "林佳", "黄睿", "郑昊"]


def name():
    s = random.choice(SURNAMES)
    if random.random() < 0.5:
        return s + random.choice(GIVEN1)
    return s + random.choice(GIVEN1) + random.choice(GIVEN2)


def next_id():
    """生成 10 位学号 1120260xxx"""
    return "112026" + str(random.randint(100, 999)).zfill(4)


def make_rows():
    rows = []
    used_ids = set()

    def fresh_id():
        sid = next_id()
        while sid in used_ids:
            sid = next_id()
        used_ids.add(sid)
        return sid

    # 1) 正常行
    for _ in range(286):
        sid = fresh_id()
        only_one = random.random() < 0.22  # 约 22% 只填一个志愿
        r1 = random.choice(DEPTS)
        r2 = "" if only_one else random.choice(DEPTS)
        rows.append({
            "姓名": name(),
            "学号": sid,
            "邮箱": f"{sid}@smbu.edu.cn",
            "志愿1": r1,
            "志愿2": r2,
            "推荐人": random.choice(REFERRERS),
        })

    # 2) 学号非纯数字
    for bad in ["112o260123", "112026X456", "11202-0801", "abc260789"]:
        rows.append({"姓名": name(), "学号": bad,
                     "邮箱": f"{bad}@smbu.edu.cn",
                     "志愿1": random.choice(DEPTS), "志愿2": "",
                     "推荐人": ""})

    # 3) 学号为空
    for _ in range(2):
        rows.append({"姓名": name(), "学号": "",
                     "邮箱": f"someone{smbu()}",  # 邮箱也无法校验
                     "志愿1": random.choice(DEPTS), "志愿2": "",
                     "推荐人": ""})

    # 4) 学号纯数字但 11 位（工具不校验位数 → 正常）
    rows.append({"姓名": name(), "学号": "11202601234",
                 "邮箱": "11202601234@smbu.edu.cn",
                 "志愿1": "技术部", "志愿2": "", "推荐人": ""})
    # 学号尾随空格（工具去空白 → 正常）
    rows.append({"姓名": name(), "学号": "1120260567 ",
                 "邮箱": "1120260567@smbu.edu.cn",
                 "志愿1": "宣传部", "志愿2": "", "推荐人": ""})

    # 5) 邮箱与学号不匹配
    bad_email_rows = [
        ("1120260201", "1120260201@qq.com"),
        ("1120260202", "1120260202@gmail.com"),
        ("1120260203", "1120260204@smbu.edu.cn"),  # 数字与学号不符
        ("1120260204", ""),                         # 邮箱为空
        ("1120260205", "not-an-email"),
    ]
    for sid, em in bad_email_rows:
        used_ids.add(sid)
        rows.append({"姓名": name(), "学号": sid, "邮箱": em,
                     "志愿1": random.choice(DEPTS), "志愿2": "",
                     "推荐人": ""})
    # 邮箱大写域名（工具大小写不敏感 → 正常）
    sid = fresh_id()
    rows.append({"姓名": name(), "学号": sid,
                 "邮箱": f"{sid}@SMBU.edu.cn",
                 "志愿1": "技术部", "志愿2": "", "推荐人": ""})

    # 6) 完全重复行 3 组（复制 3 条已有正常行）
    for _ in range(3):
        rows.append(dict(random.choice(rows[:286])))

    # 7) 同一学号但信息不同 2 组
    for _ in range(2):
        sid = fresh_id()
        rows.append({"姓名": name(), "学号": sid,
                     "邮箱": f"{sid}@smbu.edu.cn",
                     "志愿1": "技术部", "志愿2": "宣传部", "推荐人": ""})
        rows.append({"姓名": name(), "学号": sid,
                     "邮箱": f"{sid}@smbu.edu.cn",
                     "志愿1": "学术部", "志愿2": "", "推荐人": "李娜"})

    # 8) 姓名空 / 志愿1 空（用于概览空值统计与统计分组）
    for _ in range(2):
        sid = fresh_id()
        rows.append({"姓名": "", "学号": sid,
                     "邮箱": f"{sid}@smbu.edu.cn",
                     "志愿1": random.choice(DEPTS), "志愿2": "",
                     "推荐人": ""})
    for _ in range(3):
        sid = fresh_id()
        rows.append({"姓名": name(), "学号": sid,
                     "邮箱": f"{sid}@smbu.edu.cn",
                     "志愿1": "", "志愿2": random.choice(DEPTS),
                     "推荐人": ""})

    random.shuffle(rows)
    return rows


def smbu():
    return f"{random.randint(100000, 999999)}@smbu.edu.cn"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    base = os.path.dirname(here)
    out = os.path.join(base, "data", "raw", "2026-recruit-signup.csv")
    rows = make_rows()
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"已生成 {len(rows)} 行模拟报名数据 -> {out}")


if __name__ == "__main__":
    main()
