#!/usr/bin/env python
"""检查病例的检查选项数据"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption

# 获取病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.case_id} - {case.title}")

# 查询该病例的检查选项
exam_options = ExaminationOption.objects.filter(clinical_case=case)
print(f"\n检查选项数量: {exam_options.count()}")

if exam_options.exists():
    print("\n现有检查选项:")
    for opt in exam_options:
        print(f"  - {opt.examination_name} ({opt.examination_type})")
        print(f"    诊断价值: {opt.get_diagnostic_value_display()}")
        print(f"    必选: {opt.is_required}")
        print()
else:
    print("\n⚠️  该病例暂无检查选项数据")
    print("需要添加检查选项（包括正确的检查和干扰项）")
