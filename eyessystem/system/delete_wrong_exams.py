#!/usr/bin/env python
"""删除错误添加的B超和角膜内皮细胞计数检查"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption

# 获取病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.case_id} - {case.title}\n")

# 删除B超检查和角膜内皮细胞计数
to_delete = ['B超检查', '角膜内皮细胞计数']
for exam_name in to_delete:
    result = ExaminationOption.objects.filter(
        clinical_case=case,
        examination_name=exam_name
    ).delete()
    if result[0] > 0:
        print(f"✓ 已删除: {exam_name}")
    else:
        print(f"- 未找到: {exam_name}")

print("\n✅ 删除完成")

# 显示剩余的检查选项
remaining = ExaminationOption.objects.filter(clinical_case=case)
print(f"\n剩余检查选项 ({remaining.count()} 项):")
for opt in remaining:
    print(f"  - {opt.examination_name}")
