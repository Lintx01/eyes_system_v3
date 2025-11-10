"""
验证重置逻辑是否会触发
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession

session = StudentClinicalSession.objects.get(id=11)

print(f"会话ID: {session.id}")
print(f"状态: {session.session_status}")
print(f"完成时间: {session.completed_at}")
print(f"完成时间不为空: {session.completed_at is not None}")
print(f"状态为completed: {session.session_status == 'completed'}")
print(f"应该重置: {session.session_status == 'completed' or session.completed_at is not None}")
