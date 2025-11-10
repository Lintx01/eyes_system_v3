"""
检查最新的诊断测试记录
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession, ClinicalCase, DiagnosisOption
from django.contrib.auth.models import User

print("=" * 80)
print("最新诊断测试记录检查")
print("=" * 80)

# 获取所有学生
students = User.objects.filter(groups__name='Students')

for student in students:
    print(f"\n【学生: {student.username}】")
    
    # 获取该学生最新的会话
    latest_session = StudentClinicalSession.objects.filter(
        student=student
    ).order_by('-id').first()
    
    if not latest_session:
        print("  无学习记录")
        continue
    
    print(f"  病例: {latest_session.clinical_case.title}")
    print(f"  诊断尝试次数: {latest_session.diagnosis_attempt_count}")
    print(f"  诊断得分: {latest_session.diagnosis_score}")
    print(f"  会话状态: {latest_session.session_status}")
    print(f"  选择的诊断IDs: {latest_session.selected_diagnoses}")
    
    # 获取该病例的诊断选项
    if latest_session.selected_diagnoses:
        print(f"\n  选择的诊断详情:")
        for diag_id in latest_session.selected_diagnoses:
            try:
                diag = DiagnosisOption.objects.get(id=diag_id)
                correct_mark = "✓" if diag.is_correct_diagnosis else "✗"
                print(f"    {correct_mark} {diag.diagnosis_name} (ID: {diag_id})")
            except DiagnosisOption.DoesNotExist:
                print(f"    ⚠ ID {diag_id} 不存在")
    
    # 显示该病例的所有正确诊断
    correct_diagnoses = DiagnosisOption.objects.filter(
        clinical_case=latest_session.clinical_case,
        is_correct_diagnosis=True
    )
    print(f"\n  该病例的正确诊断:")
    for diag in correct_diagnoses:
        print(f"    ✓ {diag.diagnosis_name} (ID: {diag.id})")
    
    # 分析
    if latest_session.selected_diagnoses:
        selected_ids = set(latest_session.selected_diagnoses)
        correct_ids = set(correct_diagnoses.values_list('id', flat=True))
        
        if selected_ids == correct_ids:
            print(f"\n  ✓ 选择完全正确")
            expected_score = max(100 - (latest_session.diagnosis_attempt_count - 1) * 10, 60)
            print(f"  期望得分: {expected_score}分")
            print(f"  实际得分: {latest_session.diagnosis_score}分")
            if abs(latest_session.diagnosis_score - expected_score) > 0.1:
                print(f"  ⚠️ 得分异常！")
        else:
            print(f"\n  ✗ 选择不完全正确")
            print(f"  多选的: {selected_ids - correct_ids}")
            print(f"  漏选的: {correct_ids - selected_ids}")

print("\n" + "=" * 80)
