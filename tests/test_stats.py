# -*- coding: utf-8 -*-
"""需求3（统计与导出）的单元测试"""
import os
import tempfile
import unittest

from recruit_tool import (
    load_csv, validate_rows, stats_by_first_choice, volunteer_fill_stats,
)


def write_csv(text):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    return path


CSV_3 = (
    "姓名,学号,邮箱,志愿1,志愿2,推荐人\n"
    # 正常行：4 行
    "张伟,1120260001,1120260001@smbu.edu.cn,技术部,宣传部,李娜\n"   # 两志愿都填
    "李娜,1120260002,1120260002@smbu.edu.cn,技术部,,\n"             # 只填志愿1
    "王强,1120260003,1120260003@smbu.edu.cn,学术部,技术部,刘洋\n"   # 两志愿都填
    "刘洋,1120260004,1120260004@smbu.edu.cn,外联部,,\n"             # 只填志愿1
    # 问题行（学号非纯数字，会被清洗掉）
    "陈静,112X60005,112X60005@smbu.edu.cn,技术部,学术部,\n"
)


class TestStats(unittest.TestCase):

    def setUp(self):
        self.path = write_csv(CSV_3)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def _clean(self):
        rows, nums = load_csv(self.path)
        clean, problems = validate_rows(rows, nums)
        return [r for _, r in clean]

    def test_first_choice_stats(self):
        clean = self._clean()
        stats = stats_by_first_choice(clean)
        # 技术部 2、学术部 1、外联部 1
        self.assertEqual(stats["技术部"], 2)
        self.assertEqual(stats["学术部"], 1)
        self.assertEqual(stats["外联部"], 1)
        # 人数降序：技术部排第一
        self.assertEqual(list(stats.items())[0][0], "技术部")

    def test_volunteer_fill_stats(self):
        clean = self._clean()
        stats = volunteer_fill_stats(clean)
        self.assertEqual(stats["两个志愿都填"], 2)
        self.assertEqual(stats["只填第一志愿"], 2)
        self.assertEqual(stats["只填第二志愿"], 0)
        self.assertEqual(stats["两个志愿都没填"], 0)

    def test_clean_excludes_problem_rows(self):
        clean = self._clean()
        # 问题行（陈静）被清洗掉，剩 4 行
        self.assertEqual(len(clean), 4)


if __name__ == "__main__":
    unittest.main()
