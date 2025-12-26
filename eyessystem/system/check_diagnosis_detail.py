import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, DiagnosisOption

# 获取老年性白内障病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.title} (ID: {case.id})\n")

# 获取该病例的所有诊断选项
print("=" * 60)
print("当前病例的诊断选项:")
print("=" * 60)

options = DiagnosisOption.objects.filter(clinical_case=case)
for opt in options:
    print(f"\nID: {opt.id}")
    print(f"  名称: {opt.diagnosis_name}")
    print(f"  所属病例ID: {opt.clinical_case.id}")
    print(f"  所属病例名称: {opt.clinical_case.title}")
    print(f"  is_correct_diagnosis: {opt.is_correct_diagnosis}")
    print(f"  诊断描述: {opt.diagnosis_description[:100] if opt.diagnosis_description else '无'}")

print("\n" + "=" * 60)
print("检查ID=11的诊断选项:")
print("=" * 60)

opt_11 = DiagnosisOption.objects.get(id=11)
print(f"\nID: 11")
print(f"  名称: {opt_11.diagnosis_name}")
print(f"  所属病例ID: {opt_11.clinical_case.id}")
print(f"  所属病例名称: {opt_11.clinical_case.title}")
print(f"  is_correct_diagnosis: {opt_11.is_correct_diagnosis}")
