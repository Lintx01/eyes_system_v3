#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import TreatmentOption

print("=== 治疗选项配置检查 ===")
treatments = TreatmentOption.objects.all()

for t in treatments:
    print(f"治疗方案: {t.treatment_name}")
    print(f"  案例: {t.clinical_case.title}")
    print(f"  is_optimal (最佳): {t.is_optimal}")
    print(f"  is_acceptable (可接受): {t.is_acceptable}")
    print(f"  is_contraindicated (禁忌): {t.is_contraindicated}")
    print(f"  疗效评分: {t.efficacy_score}")
    print("  ---")

print(f"总共 {treatments.count()} 个治疗选项")