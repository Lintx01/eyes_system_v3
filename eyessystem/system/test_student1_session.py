import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.contrib.auth import get_user_model
from cases.models import ClinicalCase, StudentClinicalSession

User = get_user_model()

# 获取student1用户
student = User.objects.get(username='student1')
print(f"用户: {student.username}")

# 获取老年性白内障病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.case_id} - {case.title}")

# 获取会话
try:
    session = StudentClinicalSession.objects.get(
        student=student,
        clinical_case=case
    )
    print(f"\n✓ 找到会话")
    print(f"  session.session_status = '{session.session_status}'")
    print(f"  session.id = {session.id}")
    
    # 检查阶段判断
    forbidden_chat_stages = ['diagnosis_reasoning', 'treatment_selection', 'learning_feedback', 'completed']
    
    if session.session_status in forbidden_chat_stages:
        print(f"\n❌ 后端判断: 当前阶段 '{session.session_status}' 不允许聊天")
    else:
        print(f"\n✓ 后端判断: 当前阶段 '{session.session_status}' 允许聊天")
        
except StudentClinicalSession.DoesNotExist:
    print("\n✗ 未找到会话")
