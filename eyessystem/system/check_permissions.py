#!/usr/bin/env python
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.contrib.auth.models import User, Group
from cases.views import is_teacher, is_student

print("=== 用户权限检查 ===")

# 检查所有用户组
groups = Group.objects.all()
print(f"系统用户组数量: {groups.count()}")
for group in groups:
    print(f"- 用户组: {group.name}, 成员数量: {group.user_set.count()}")
    for user in group.user_set.all():
        print(f"  └── {user.username}")

print("\n=== 超级用户检查 ===")
superusers = User.objects.filter(is_superuser=True)
print(f"超级用户数量: {superusers.count()}")
for user in superusers:
    print(f"- {user.username}: 超级用户={user.is_superuser}, 活跃={user.is_active}")

print("\n=== 当前用户权限状态 ===")
users = User.objects.all()
for user in users:
    is_teacher_result = is_teacher(user)
    is_student_result = is_student(user)
    print(f"用户: {user.username}")
    print(f"  - 是否为教师: {is_teacher_result}")
    print(f"  - 是否为学生: {is_student_result}")
    print(f"  - 是否为超级用户: {user.is_superuser}")
    print(f"  - 所属组: {[g.name for g in user.groups.all()]}")
    print()