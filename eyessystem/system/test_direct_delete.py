#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置Django
django.setup()

from cases.models import ClinicalCase
from django.db import transaction

def test_delete():
    print("=== 删除测试开始 ===")
    
    # 选择一个测试案例进行删除
    test_case_id = "OCT_TEST_CASE"  # 选择测试案例
    
    try:
        case = ClinicalCase.objects.get(case_id=test_case_id)
        print(f"找到案例: {case.case_id} - {case.title}")
        print(f"案例创建者: {case.created_by}")
        print(f"案例状态: {'启用' if case.is_active else '禁用'}")
        
        # 检查相关数据
        from cases.models import StudentClinicalSession
        sessions = StudentClinicalSession.objects.filter(clinical_case=case)
        print(f"关联的学生会话数量: {sessions.count()}")
        
        # 检查其他相关数据
        examination_options = case.examination_options.all()
        diagnosis_options = case.diagnosis_options.all() 
        treatment_options = case.treatment_options.all()
        
        print(f"检查选项数量: {examination_options.count()}")
        print(f"诊断选项数量: {diagnosis_options.count()}")
        print(f"治疗选项数量: {treatment_options.count()}")
        
        print("\n=== 尝试删除 ===")
        
        # 使用事务确保原子性
        with transaction.atomic():
            # 记录删除前的总数
            total_before = ClinicalCase.objects.count()
            print(f"删除前总案例数: {total_before}")
            
            # 执行删除
            case.delete()
            
            # 检查删除后的总数
            total_after = ClinicalCase.objects.count()
            print(f"删除后总案例数: {total_after}")
            
            if total_after == total_before - 1:
                print("✅ 删除成功！")
            else:
                print("❌ 删除失败，数量没有变化")
                
        # 再次确认删除
        try:
            ClinicalCase.objects.get(case_id=test_case_id)
            print("❌ 案例仍然存在！删除未生效")
        except ClinicalCase.DoesNotExist:
            print("✅ 确认案例已被删除")
            
    except ClinicalCase.DoesNotExist:
        print(f"❌ 未找到案例: {test_case_id}")
    except Exception as e:
        print(f"❌ 删除过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

def test_permissions():
    print("\n=== 权限检查 ===")
    from django.contrib.auth.models import User
    
    # 检查是否有用户
    users = User.objects.all()
    print(f"系统用户数量: {users.count()}")
    
    for user in users:
        print(f"用户: {user.username} - 是否为教师: {user.groups.filter(name='teachers').exists()}")

if __name__ == "__main__":
    test_delete()
    test_permissions()