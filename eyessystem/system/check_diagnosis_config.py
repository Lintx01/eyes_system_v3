"""
检查诊断配置是否合理
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, DiagnosisOption

print("=" * 80)
print("诊断配置检查报告")
print("=" * 80)

cases = ClinicalCase.objects.all()
issues_found = []

for case in cases:
    print(f"\n【病例：{case.title}】")
    print(f"案例ID: {case.case_id}")
    
    correct_diagnoses = DiagnosisOption.objects.filter(
        clinical_case=case, 
        is_correct_diagnosis=True
    )
    
    incorrect_diagnoses = DiagnosisOption.objects.filter(
        clinical_case=case, 
        is_correct_diagnosis=False
    )
    
    print(f"\n✓ 正确诊断 ({correct_diagnoses.count()}个):")
    for d in correct_diagnoses:
        required_mark = "【必需】" if d.is_required else "【可选】"
        print(f"  - {d.diagnosis_name} {required_mark}")
    
    print(f"\n✗ 干扰选项 ({incorrect_diagnoses.count()}个):")
    for d in incorrect_diagnoses:
        print(f"  - {d.diagnosis_name}")
    
    # 检查潜在问题
    if correct_diagnoses.count() == 0:
        issue = f"⚠️ 警告: 病例'{case.title}'没有配置任何正确诊断！"
        print(f"\n{issue}")
        issues_found.append(issue)
    
    if correct_diagnoses.count() > 1:
        info = f"ℹ️ 提示: 病例'{case.title}'有{correct_diagnoses.count()}个正确诊断，学生必须全部选中才能得满分"
        print(f"\n{info}")
    
    # 检查病例名称与诊断名称的匹配
    case_title_lower = case.title.lower()
    diagnosis_names = [d.diagnosis_name.lower() for d in correct_diagnoses]
    
    # 简单的名称匹配检查
    if not any(name in case_title_lower or case_title_lower in name for name in diagnosis_names):
        issue = f"⚠️ 警告: 病例名称'{case.title}'与正确诊断名称不匹配！"
        print(f"\n{issue}")
        issues_found.append(issue)

print("\n" + "=" * 80)
print("检查完成！")
if issues_found:
    print(f"\n发现 {len(issues_found)} 个潜在问题：")
    for i, issue in enumerate(issues_found, 1):
        print(f"{i}. {issue}")
else:
    print("\n未发现明显问题。")
print("=" * 80)
