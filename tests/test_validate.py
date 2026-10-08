# -*- coding: utf-8 -*-
"""需求2（校验与清洗）的单元测试"""
import os
import tempfile
import unittest

from recruit_tool import (
    load_csv, validate_rows,
    REASON_ID_MISSING, REASON_ID_NOT_DIGIT,
    REASON_EMAIL_MISSING, REASON_EMAIL_MISMATCH,
    REASON_DUP_IDENTICAL, REASON_DUP_CONFLICT,
)


def write_csv(text):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    return path


CSV_2 = (
    "姓名,学号,邮箱,志愿1,志愿2,推荐人\n"
    # 1 正常行（10位学号、邮箱匹配）
    "张伟,1120260001,1120260001@smbu.edu.cn,技术部,宣传部,李娜\n"
    # 2 学号非纯数字
    "李娜,112o260002,112o260002@smbu.edu.cn,学术部,,\n"
    # 3 学号缺失
    "王强,,someone@smbu.edu.cn,外联部,,\n"
    # 4 邮箱与学号不匹配（qq邮箱）
    "刘洋,1120260004,1120260004@qq.com,学术部,,\n"
    # 5 邮箱缺失
    "陈静,1120260005,,技术部,,\n"
    # 6 邮箱大写域名（应判为正常）
    "赵磊,1120260006,1120260006@SMBU.edu.cn,技术部,,\n"
    # 7 与第1行完全重复 -> 保留首条(行2)，本行(行8)标记重复
    "张伟,1120260001,1120260001@smbu.edu.cn,技术部,宣传部,李娜\n"
    # 8 11位纯数字学号（工具不校验位数 -> 正常）
    "孙悦,11202600123,11202600123@smbu.edu.cn,外联部,,\n"
    # 9 同学号但信息不一致（行10）
    "周航,1120260009,1120260009@smbu.edu.cn,技术部,宣传部,\n"
    # 10 同上重复学号、志愿不同 -> 两行均标记
    "周航,1120260009,1120260009@smbu.edu.cn,学术部,,李娜\n"
)


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.path = write_csv(CSV_2)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def _rows(self):
        rows, nums = load_csv(self.path)
        return rows, nums

    def test_clean_count(self):
        rows, nums = self._rows()
        clean, problems = validate_rows(rows, nums)
        # 正常行: 行2(张伟)、行7(赵磊大写邮箱)、行9(孙悦11位) 共3行进 clean
        self.assertEqual(len(clean), 3)
        clean_ids = sorted(r["学号"] for _, r in clean)
        self.assertEqual(clean_ids, ["1120260001", "1120260006", "11202600123"])

    def test_problem_reasons(self):
        rows, nums = self._rows()
        clean, problems = validate_rows(rows, nums)
        self.assertEqual(len(problems), 7)
        by_row = {p["行号"]: p["问题原因"] for p in problems}
        self.assertIn(REASON_ID_NOT_DIGIT, by_row[3])
        self.assertIn(REASON_ID_MISSING, by_row[4])
        self.assertIn(REASON_EMAIL_MISMATCH, by_row[5])
        self.assertIn(REASON_EMAIL_MISSING, by_row[6])
        self.assertIn(REASON_DUP_IDENTICAL, by_row[8])  # 重复首条保留
        # 文件行10、11 学号一致但信息不一致 -> 均标记
        self.assertIn(REASON_DUP_CONFLICT, by_row[10])
        self.assertIn(REASON_DUP_CONFLICT, by_row[11])

    def test_duplicate_identical_keeps_first(self):
        rows, nums = self._rows()
        clean, problems = validate_rows(rows, nums)
        # 行2 张伟保留，行8 张伟进问题清单
        self.assertTrue(any(r["学号"] == "1120260001" for _, r in clean))
        self.assertEqual(len(clean), 3)


if __name__ == "__main__":
    unittest.main()
