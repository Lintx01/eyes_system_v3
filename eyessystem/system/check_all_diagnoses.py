"""检查所有病例的诊断选项"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, DiagnosisOption

# 统计所有病例的诊断选项
all_cases = ClinicalCase.objects.filter(is_active=True)
print(f"活跃病例总数: {all_cases.count()}\n")

for case in all_cases:
    diagnoses = DiagnosisOption.objects.filter(clinical_case=case)
    correct = diagnoses.filter(is_correct_diagnosis=True)
    
    print(f"病例: {case.case_id} - {case.title}")
    print(f"  诊断选项总数: {diagnoses.count()}")
    print(f"  正确诊断数: {correct.count()}")
    
    if correct.exists():
        for c in correct:
            print(f"    ✓ {c.diagnosis_name}")
    
    print()

# 统计所有正确诊断
all_correct = DiagnosisOption.objects.filter(is_correct_diagnosis=True)
print(f"\n数据库中所有正确诊断总数: {all_correct.count()}")
print("\n所有正确诊断列表:")
for diag in all_correct:
    print(f"  - {diag.diagnosis_name} ({diag.clinical_case.case_id})")
