#!/usr/bin/env python
"""检查学生会话的阶段状态"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession, ClinicalCase
from django.contrib.auth import get_user_model

User = get_user_model()

# 查找所有用户（不过滤类型）
students = User.objects.all()
print(f"找到 {students.count()} 个用户\n")

for student in students:
    print(f"学生: {student.username}")
    sessions = StudentClinicalSession.objects.filter(student=student)
    print(f"  会话数量: {sessions.count()}")
    
    for session in sessions:
        print(f"  - 病例: {session.clinical_case.case_id}")
        print(f"    阶段: {session.session_status}")
        print()
