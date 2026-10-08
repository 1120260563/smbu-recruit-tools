# -*- coding: utf-8 -*-
"""需求1（读入与概览）的单元测试"""
import os
import tempfile
import unittest

from recruit_tool import load_csv, overview_summary, REQUIRED_COLUMNS


def write_csv(text):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    return path


CSV_1 = (
    "姓名,学号,邮箱,志愿1,志愿2,推荐人\n"
    "张伟,1120260001,1120260001@smbu.edu.cn,技术部,宣传部,李娜\n"
    ",1120260002,1120260002@smbu.edu.cn,学术部,,\n"          # 姓名空、志愿2空
    "王强,1120260003,1120260003@smbu.edu.cn,外联部,学术部,刘洋\n"
    "张伟,1120260001,1120260001@smbu.edu.cn,技术部,宣传部,李娜\n"  # 与第1行完全重复
    "陈静,,someone@smbu.edu.cn,技术部,,\n"                    # 学号空
)


class TestOverview(unittest.TestCase):

    def setUp(self):
        self.path = write_csv(CSV_1)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_load_csv(self):
        rows, nums = load_csv(self.path)
        self.assertEqual(len(rows), 5)
        self.assertEqual(nums, [2, 3, 4, 5, 6])
        # 尾随空白应被去除
        self.assertEqual(rows[0]["学号"], "1120260001")
        self.assertEqual(rows[1]["姓名"], "")
        self.assertEqual(rows[4]["学号"], "")

    def test_missing_column(self):
        bad = write_csv("姓名,学号,邮箱\n张伟,1,a@b.cn\n")
        with self.assertRaises(SystemExit):
            load_csv(bad)
        os.remove(bad)

    def test_total_and_nulls(self):
        rows, nums = load_csv(self.path)
        info = overview_summary(rows, nums)
        self.assertEqual(info["total"], 5)
        self.assertEqual(info["nulls"]["姓名"], 1)
        self.assertEqual(info["nulls"]["学号"], 1)
        self.assertEqual(info["nulls"]["邮箱"], 0)
        self.assertEqual(info["nulls"]["志愿2"], 2)  # 行2、行5

    def test_duplicate_groups(self):
        rows, nums = load_csv(self.path)
        info = overview_summary(rows, nums)
        self.assertEqual(len(info["dup_groups"]), 1)
        key, members = info["dup_groups"][0]
        self.assertEqual(sorted(members), [2, 5])


if __name__ == "__main__":
    unittest.main()
