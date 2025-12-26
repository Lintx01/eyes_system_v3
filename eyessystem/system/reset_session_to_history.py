#!/usr/bin/env python
"""重置会话阶段为病史采集阶段"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession
from django.contrib.auth import get_user_model

User = get_user_model()

# 找到用户 2020281072
user = User.objects.get(username='2020281072')
print(f"找到用户: {user.username}")

# 找到该用户的 CCC7D361F8 会话
session = StudentClinicalSession.objects.get(
    student=user,
    clinical_case__case_id='CCC7D361F8'
)

print(f"当前阶段: {session.session_status}")

# 重置为病史采集阶段
session.session_status = 'case_presentation'
session.save()

print(f"已重置为: {session.session_status}")
print("✅ 完成！现在可以重新开始病史采集了。")
