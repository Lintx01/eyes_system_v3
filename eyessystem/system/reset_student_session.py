"""
重置指定学生的特定病例学习记录
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession, ClinicalCase
from django.contrib.auth.models import User

print("=" * 80)
print("重置学生学习记录")
print("=" * 80)

# 可以修改这里来指定要重置的学生和病例
STUDENT_USERNAME = 'student3'
CASE_TITLE = '老年性白内障'

try:
    student = User.objects.get(username=STUDENT_USERNAME)
    case = ClinicalCase.objects.get(title=CASE_TITLE)
    
    # 查找该学生在该病例的会话
    sessions = StudentClinicalSession.objects.filter(
        student=student,
        clinical_case=case
    )
    
    if not sessions.exists():
        print(f"\n未找到 {STUDENT_USERNAME} 在 {CASE_TITLE} 的学习记录")
    else:
        print(f"\n找到 {sessions.count()} 条学习记录:")
        for session in sessions:
            print(f"  ID: {session.id}")
            print(f"  诊断尝试: {session.diagnosis_attempt_count}次")
            print(f"  诊断得分: {session.diagnosis_score}分")
            print(f"  状态: {session.session_status}")
        
        confirm = input(f"\n确定要删除这些记录吗？(yes/no): ")
        if confirm.lower() == 'yes':
            count = sessions.count()
            sessions.delete()
            print(f"\n✓ 已删除 {count} 条记录")
            print(f"\n{STUDENT_USERNAME} 现在可以重新开始学习 {CASE_TITLE}")
        else:
            print("\n取消操作")

except User.DoesNotExist:
    print(f"\n✗ 未找到用户: {STUDENT_USERNAME}")
except ClinicalCase.DoesNotExist:
    print(f"\n✗ 未找到病例: {CASE_TITLE}")

print("\n" + "=" * 80)
