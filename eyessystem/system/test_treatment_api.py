"""
测试治疗方案API
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'system.settings')
django.setup()

from cases.models import ClinicalCase, TreatmentOption

def test_treatment_options():
    """测试治疗选项是否存在"""
    print("=== 测试治疗选项数据 ===\n")
    
    # 获取所有病例
    cases = ClinicalCase.objects.filter(is_active=True)
    print(f"活跃病例数量: {cases.count()}\n")
    
    for case in cases:
        print(f"\n病例: {case.case_id} - {case.case_title}")
        print("-" * 60)
        
        # 获取该病例的所有治疗选项
        treatments = TreatmentOption.objects.filter(clinical_case=case)
        print(f"治疗选项数量: {treatments.count()}")
        
        if treatments.exists():
            # 显示最佳治疗
            optimal_treatments = treatments.filter(is_optimal=True)
            print(f"\n最佳治疗方案 ({optimal_treatments.count()}个):")
            for treatment in optimal_treatments:
                print(f"  - ID:{treatment.id} | {treatment.treatment_name}")
                print(f"    类型: {treatment.treatment_type}")
                print(f"    描述: {treatment.treatment_description[:50] if treatment.treatment_description else '无'}...")
                print(f"    有依据: {'是' if treatment.correct_rationale else '否'}")
                print(f"    有关键点: {'是' if treatment.key_points else '否'}")
                print(f"    难度: {treatment.difficulty_level or '未设置'}")
                print()
            
            # 显示可接受治疗
            acceptable_treatments = treatments.filter(is_acceptable=True, is_optimal=False)
            if acceptable_treatments.exists():
                print(f"可接受治疗方案 ({acceptable_treatments.count()}个):")
                for treatment in acceptable_treatments:
                    print(f"  - ID:{treatment.id} | {treatment.treatment_name}")
                print()
        else:
            print("  ⚠️ 警告: 该病例没有治疗选项！")


def test_treatment_api_logic():
    """测试治疗API逻辑"""
    print("\n" + "=" * 60)
    print("=== 测试治疗API逻辑 ===\n")
    
    # 找一个有治疗选项的病例
    case = ClinicalCase.objects.filter(is_active=True).first()
    
    if not case:
        print("没有活跃的病例")
        return
    
    print(f"测试病例: {case.case_id} - {case.case_title}\n")
    
    # 模拟API返回的数据
    from cases.treatment_views import get_treatment_options
    from django.contrib.auth.models import User
    from django.test import RequestFactory
    
    # 创建一个测试请求
    factory = RequestFactory()
    request = factory.get(f'/api/clinical/case/{case.case_id}/treatment-options/')
    
    # 获取或创建一个学生用户
    student = User.objects.filter(is_staff=False).first()
    if not student:
        student = User.objects.create_user(
            username='test_student',
            password='test123',
            is_staff=False
        )
        print(f"创建测试学生用户: {student.username}")
    
    request.user = student
    
    # 调用API视图
    response = get_treatment_options(request, case.case_id)
    
    # 解析响应
    import json
    response_data = json.loads(response.content.decode('utf-8'))
    
    print("API响应:")
    print(f"  成功: {response_data.get('success')}")
    print(f"  消息: {response_data.get('message')}")
    
    if response_data.get('success'):
        data = response_data.get('data', {})
        treatment_options = data.get('treatment_options', [])
        print(f"\n返回的治疗选项数量: {len(treatment_options)}")
        print(f"最佳治疗数量: {data.get('optimal_count')}")
        print(f"总选项数量: {data.get('total_count')}")
        
        if treatment_options:
            print("\n治疗选项列表:")
            for idx, option in enumerate(treatment_options, 1):
                print(f"  {idx}. ID:{option['id']} | {option['name']}")
                print(f"     类型: {option['type']} | 难度: {option.get('difficulty', '未知')}")
    else:
        print(f"  错误: {response_data.get('message')}")


if __name__ == '__main__':
    test_treatment_options()
    test_treatment_api_logic()
