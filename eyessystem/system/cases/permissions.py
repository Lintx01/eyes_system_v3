"""
权限管理脚本 - 眼科教学系统
使用方法：
1. 在Django shell中运行：python manage.py shell
2. 导入并执行：from cases.permissions import setup_groups_and_permissions; setup_groups_and_permissions()
"""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from .models import Case, Exercise, ExamRecord, UserProgress, UserAnswer


def setup_groups_and_permissions():
    """设置用户组和权限"""
    
    # 创建用户组
    teachers_group, created = Group.objects.get_or_create(name='Teachers')
    students_group, created = Group.objects.get_or_create(name='Students')
    
    print("用户组创建完成：Teachers, Students")
    
    # 获取模型的Content Types
    case_ct = ContentType.objects.get_for_model(Case)
    exercise_ct = ContentType.objects.get_for_model(Exercise)
    exam_record_ct = ContentType.objects.get_for_model(ExamRecord)
    user_progress_ct = ContentType.objects.get_for_model(UserProgress)
    user_answer_ct = ContentType.objects.get_for_model(UserAnswer)
    
    # 教师权限 - 可以管理所有内容
    teacher_permissions = [
        # Case 权限
        'add_case', 'change_case', 'delete_case', 'view_case',
        # Exercise 权限
        'add_exercise', 'change_exercise', 'delete_exercise', 'view_exercise',
        # ExamRecord 权限
        'view_examrecord', 'change_examrecord',
        # UserProgress 权限
        'view_userprogress', 'change_userprogress',
        # UserAnswer 权限
        'view_useranswer',
    ]
    
    # 学生权限 - 只能查看和创建自己的记录
    student_permissions = [
        # Case 权限 - 只读
        'view_case',
        # Exercise 权限 - 只读
        'view_exercise',
        # ExamRecord 权限 - 可以创建和查看自己的
        'add_examrecord', 'view_examrecord',
        # UserProgress 权限 - 可以查看和更新自己的
        'view_userprogress', 'change_userprogress',
        # UserAnswer 权限 - 可以创建自己的答案
        'add_useranswer', 'view_useranswer',
    ]
    
    # 为教师组分配权限
    for perm_codename in teacher_permissions:
        try:
            perm = Permission.objects.get(codename=perm_codename)
            teachers_group.permissions.add(perm)
        except Permission.DoesNotExist:
            print(f"权限 {perm_codename} 不存在")
    
    # 为学生组分配权限
    for perm_codename in student_permissions:
        try:
            perm = Permission.objects.get(codename=perm_codename)
            students_group.permissions.add(perm)
        except Permission.DoesNotExist:
            print(f"权限 {perm_codename} 不存在")
    
    print("权限分配完成！")
    print(f"教师组权限数量: {teachers_group.permissions.count()}")
    print(f"学生组权限数量: {students_group.permissions.count()}")
    
    return teachers_group, students_group


def create_test_users():
    """创建测试用户"""
    
    # 确保用户组存在
    teachers_group = Group.objects.get(name='Teachers')
    students_group = Group.objects.get(name='Students')
    
    # 创建测试教师
    teacher_user, created = User.objects.get_or_create(
        username='teacher1',
        defaults={
            'first_name': '张',
            'last_name': '教授',
            'email': 'teacher@example.com',
            'is_staff': True,  # 可以访问admin
        }
    )
    
    if created:
        teacher_user.set_password('teacher123')
        teacher_user.save()
        print("创建测试教师账户: teacher1, 密码: teacher123")
    
    teacher_user.groups.add(teachers_group)
    
    # 创建测试学生
    for i in range(1, 4):  # 创建3个学生
        student_user, created = User.objects.get_or_create(
            username=f'student{i}',
            defaults={
                'first_name': f'学生{i}',
                'last_name': '',
                'email': f'student{i}@example.com',
            }
        )
        
        if created:
            student_user.set_password('student123')
            student_user.save()
            print(f"创建测试学生账户: student{i}, 密码: student123")
        
        student_user.groups.add(students_group)
    
    print("测试用户创建完成！")


def assign_user_to_group(username, group_name):
    """将用户分配到指定组"""
    try:
        user = User.objects.get(username=username)
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
        print(f"用户 {username} 已添加到 {group_name} 组")
    except User.DoesNotExist:
        print(f"用户 {username} 不存在")
    except Group.DoesNotExist:
        print(f"用户组 {group_name} 不存在")


if __name__ == "__main__":
    print("请在Django shell中运行此脚本的函数")
    print("示例：")
    print("from cases.permissions import setup_groups_and_permissions, create_test_users")
    print("setup_groups_and_permissions()")
    print("create_test_users()")