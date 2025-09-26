#!/usr/bin/env python
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import Exercise

print("检查数据库中的练习题选项格式:")
print("=" * 50)

exercises = Exercise.objects.all()
if not exercises:
    print("数据库中没有练习题数据")
else:
    for ex in exercises[:3]:  # 只显示前3个
        print(f"题目: {ex.question[:50]}...")
        print(f"选项: {ex.get_options_list()}")
        print(f"正确答案: {ex.correct_answer}")
        print("-" * 30)