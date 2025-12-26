import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.contrib.auth import get_user_model
from cases.models import ClinicalCase, StudentClinicalSession

User = get_user_model()

# 获取学生用户
student = User.objects.filter(is_staff=False).first()
print(f"测试学生: {student.username}")

# 获取病例
case = ClinicalCase.objects.filter(is_active=True).first()
print(f"测试病例: {case.case_id} - {case.title}")

# 获取会话
try:
    session = StudentClinicalSession.objects.get(
        student=student,
        clinical_case=case
    )
    print(f"\n当前会话状态: '{session.session_status}'")
    print(f"会话状态类型: {type(session.session_status)}")
    
    # 检查阶段判断逻辑
    forbidden_chat_stages = ['diagnosis_reasoning', 'treatment_selection', 'learning_feedback', 'completed']
    allowed_chat_stages = ['case_presentation', 'examination_selection', 'examination_results']
    
    print(f"\n禁止聊天阶段: {forbidden_chat_stages}")
    print(f"允许聊天阶段: {allowed_chat_stages}")
    
    print(f"\n判断结果:")
    print(f"  session.session_status in forbidden_chat_stages: {session.session_status in forbidden_chat_stages}")
    print(f"  session.session_status in allowed_chat_stages: {session.session_status in allowed_chat_stages}")
    
    if session.session_status in forbidden_chat_stages:
        print(f"\n❌ 当前阶段 '{session.session_status}' 不允许聊天")
    else:
        print(f"\n✓ 当前阶段 '{session.session_status}' 允许聊天")
        
except StudentClinicalSession.DoesNotExist:
    print("\n未找到会话，将创建新会话（默认状态：case_presentation）")
    print("✓ 默认阶段允许聊天")
