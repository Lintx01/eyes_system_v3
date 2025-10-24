#!/usr/bin/env python
"""
测试删除临床推理病例的脚本
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

from cases.models import ClinicalCase

def test_delete_case(case_id):
    """测试删除指定ID的病例"""
    try:
        print(f"=== 测试删除病例 {case_id} ===")
        
        # 查找病例
        case = ClinicalCase.objects.get(case_id=case_id)
        print(f"找到病例: {case.title}")
        print(f"病例对象: {case}")
        print(f"病例类型: {type(case)}")
        
        # 检查相关数据
        exam_options = case.examination_options.all()
        diagnosis_options = case.diagnosis_options.all() 
        treatment_options = case.treatment_options.all()
        
        print(f"检查选项: {exam_options.count()}")
        print(f"诊断选项: {diagnosis_options.count()}")
        print(f"治疗选项: {treatment_options.count()}")
        
        # 尝试删除
        print("开始删除...")
        deleted_count, deleted_details = case.delete()
        
        print(f"删除成功! 删除计数: {deleted_count}")
        print(f"删除详情: {deleted_details}")
        
        # 验证删除
        try:
            ClinicalCase.objects.get(case_id=case_id)
            print("错误: 病例仍然存在!")
        except ClinicalCase.DoesNotExist:
            print("确认: 病例已成功删除")
            
    except ClinicalCase.DoesNotExist:
        print(f"错误: 找不到病例 {case_id}")
    except Exception as e:
        print(f"删除失败: {e}")
        import traceback
        traceback.print_exc()

def list_all_cases():
    """列出所有病例"""
    cases = ClinicalCase.objects.all()
    print(f"=== 所有临床推理病例 ({cases.count()}) ===")
    for case in cases:
        print(f"- {case.case_id}: {case.title}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        case_id = sys.argv[1]
        test_delete_case(case_id)
    else:
        list_all_cases()