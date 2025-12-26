"""检查实际的聊天API请求和会话状态"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.contrib.auth import get_user_model
from cases.models import ClinicalCase, StudentClinicalSession

User = get_user_model()

# 获取学生用户
student = User.objects.filter(username='student1').first()
print(f"学生: {student.username}")

# 获取病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.case_id} - {case.title}")

# 获取会话
try:
    session = StudentClinicalSession.objects.get(
        student=student,
        clinical_case=case
    )
    print(f"\n当前会话状态: '{session.session_status}'")
    
    # 模拟chat_api的检查逻辑
    forbidden_chat_stages = ['diagnosis_reasoning', 'treatment_selection', 'learning_feedback', 'completed']
    
    print(f"\n禁止聊天的阶段列表: {forbidden_chat_stages}")
    print(f"当前状态是否在禁止列表中: {session.session_status in forbidden_chat_stages}")
    
    if session.session_status in forbidden_chat_stages:
        print(f"\n❌ 聊天被阻止! 当前阶段 '{session.session_status}' 在禁止列表中")
    else:
        print(f"\n✅ 聊天应该被允许! 当前阶段 '{session.session_status}' 不在禁止列表中")
        
except StudentClinicalSession.DoesNotExist:
    print("\n未找到会话")
