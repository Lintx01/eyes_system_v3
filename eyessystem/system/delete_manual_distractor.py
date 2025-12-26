#!/usr/bin/env python
"""删除手动添加的干扰项OCT扫描，只保留正确的检查选项"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption

# 获取病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.case_id} - {case.title}\n")

# 删除OCT扫描（手动添加的干扰项）
result = ExaminationOption.objects.filter(
    clinical_case=case,
    examination_name='OCT扫描'
).delete()

if result[0] > 0:
    print(f"✓ 已删除手动添加的干扰项: OCT扫描")
else:
    print(f"- OCT扫描不存在")

print("\n✅ 完成！现在只保留病例的正确检查选项")
print("干扰项将在每次加载时从其他病例的检查选项中动态随机抽取")

# 显示剩余的检查选项（只应该是正确的3项）
remaining = ExaminationOption.objects.filter(clinical_case=case)
print(f"\n病例的正确检查选项 ({remaining.count()} 项):")
for opt in remaining:
    print(f"  - {opt.examination_name} (必选: {opt.is_required})")
