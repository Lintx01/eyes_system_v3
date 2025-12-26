import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession

print("修复无效的session_status值\n")

# 查找所有使用 'history' 的会话
invalid_sessions = StudentClinicalSession.objects.filter(session_status='history')
print(f"找到 {invalid_sessions.count()} 个使用 'history' 的会话\n")

for session in invalid_sessions:
    print(f"修复: {session.student.username} - {session.clinical_case.title}")
    print(f"  从: '{session.session_status}'")
    session.session_status = 'case_presentation'
    session.save()
    print(f"  到: '{session.session_status}'")
    print()

print("✓ 修复完成")
