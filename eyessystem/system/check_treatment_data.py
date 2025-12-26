"""
快速检查治疗选项数据
"""
import os
import sys
import django

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, TreatmentOption

# 获取所有活跃病例
cases = ClinicalCase.objects.filter(is_active=True)
print(f"活跃病例数量: {cases.count()}\n")

for case in cases:
    treatments = TreatmentOption.objects.filter(clinical_case=case)
    optimal = treatments.filter(is_optimal=True).count()
    
    print(f"病例: {case.case_id} - {case.title}")
    print(f"  治疗选项总数: {treatments.count()}")
    print(f"  最佳治疗数: {optimal}")
    
    if treatments.count() == 0:
        print(f"  ⚠️ 警告: 该病例没有治疗选项！需要添加！")
    print()
