#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查选择验证系统测试脚本
验证严格的必选项检查机制是否正常工作
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption, StudentClinicalSession
from django.contrib.auth.models import User
import json


def test_validation_system():
    """测试检查选择验证系统"""
    print("=== 检查选择验证系统测试 ===\n")
    
    # 1. 查找现有案例
    print("1. 查找测试案例...")
    cases = ClinicalCase.objects.filter(is_active=True)
    if not cases.exists():
        print("   ❌ 没有找到活跃的案例")
        return False
    
    test_case = cases.first()
    print(f"   ✅ 使用案例: {test_case.title}")
    
    # 2. 检查检查项目配置
    print("\n2. 检查项目配置分析...")
    all_exams = ExaminationOption.objects.filter(clinical_case=test_case)
    required_exams = all_exams.filter(is_required=True)
    optional_exams = all_exams.filter(is_required=False)
    
    print(f"   总检查项目: {all_exams.count()}")
    print(f"   必选检查项目: {required_exams.count()}")
    print(f"   可选检查项目: {optional_exams.count()}")
    
    if required_exams.count() == 0:
        print("   ⚠️  该案例没有设置必选检查项目，将使用标准模式")
        print("   建议：为测试验证功能，请设置一些必选检查项目")
        return True
    
    print("   必选检查项目列表:")
    for exam in required_exams:
        print(f"     - {exam.examination_name} (ID: {exam.id})")
    
    # 3. 测试验证函数
    print("\n3. 测试验证逻辑...")
    
    # 模拟不同的选择场景
    test_scenarios = [
        {
            'name': '完全正确选择',
            'selected': list(required_exams.values_list('id', flat=True)),
            'should_pass': True
        },
        {
            'name': '缺少必选项',
            'selected': list(required_exams.values_list('id', flat=True)[:len(required_exams)//2]) if required_exams.count() > 1 else [],
            'should_pass': False
        },
        {
            'name': '多选非必选项',
            'selected': list(required_exams.values_list('id', flat=True)) + list(optional_exams.values_list('id', flat=True)[:2]),
            'should_pass': False
        },
        {
            'name': '完全错误选择',
            'selected': list(optional_exams.values_list('id', flat=True)[:3]),
            'should_pass': False
        }
    ]
    
    # 导入验证函数
    from cases.views import validate_examination_selection
    
    # 创建测试会话
    test_user, created = User.objects.get_or_create(
        username='test_validation_user',
        defaults={'email': 'test@example.com'}
    )
    
    test_session, created = StudentClinicalSession.objects.get_or_create(
        student=test_user,
        clinical_case=test_case,
        defaults={'session_status': 'examination'}
    )
    
    for scenario in test_scenarios:
        print(f"\n   测试场景: {scenario['name']}")
        print(f"   选择的检查项: {scenario['selected']}")
        
        required_ids = set(required_exams.values_list('id', flat=True))
        selected_ids = set(scenario['selected'])
        
        result = validate_examination_selection(
            required_ids, selected_ids, required_exams, test_session
        )
        
        passed = result['is_valid']
        expected = scenario['should_pass']
        
        if passed == expected:
            print(f"   ✅ 验证结果正确 (期望: {'通过' if expected else '失败'}, 实际: {'通过' if passed else '失败'})")
        else:
            print(f"   ❌ 验证结果错误 (期望: {'通过' if expected else '失败'}, 实际: {'通过' if passed else '失败'})")
        
        if not passed:
            print(f"   错误信息: {result.get('error_message', 'N/A')}")
            print(f"   惩罚分数: {result.get('penalty_applied', 0)}")
    
    # 4. 测试惩罚计算
    print("\n4. 测试惩罚计算...")
    
    from cases.views import calculate_examination_penalty
    
    penalty_tests = [
        {'attempts': 1, 'missing': 1, 'extra': 0, 'expected_range': (5, 15)},
        {'attempts': 2, 'missing': 2, 'extra': 1, 'expected_range': (15, 25)},
        {'attempts': 3, 'missing': 0, 'extra': 3, 'expected_range': (20, 30)},
    ]
    
    for test in penalty_tests:
        penalty = calculate_examination_penalty(
            test['attempts'], test['missing'], test['extra']
        )
        min_expected, max_expected = test['expected_range']
        
        if min_expected <= penalty <= max_expected:
            print(f"   ✅ 惩罚计算正确: {test['attempts']}次尝试, {test['missing']}缺失, {test['extra']}多选 → {penalty}分")
        else:
            print(f"   ❌ 惩罚计算异常: {test['attempts']}次尝试, {test['missing']}缺失, {test['extra']}多选 → {penalty}分 (期望: {min_expected}-{max_expected})")
    
    print("\n=== 测试完成 ===")
    return True


def show_case_statistics():
    """显示案例统计信息"""
    print("=== 案例统计信息 ===\n")
    
    all_cases = ClinicalCase.objects.filter(is_active=True)
    
    for case in all_cases:
        print(f"案例: {case.title}")
        print(f"  ID: {case.case_id}")
        
        exams = ExaminationOption.objects.filter(clinical_case=case)
        required = exams.filter(is_required=True)
        optional = exams.filter(is_required=False)
        
        print(f"  检查项目: {exams.count()} 总数")
        print(f"    - 必选: {required.count()}")
        print(f"    - 可选: {optional.count()}")
        
        if required.count() > 0:
            print("  必选项目:")
            for req in required:
                print(f"    ✓ {req.examination_name}")
        
        # 检查混合模式状态
        if required.count() > 0:
            print("  ✅ 支持混合模式验证")
        else:
            print("  ⚠️  仅支持标准模式")
        
        print()


if __name__ == '__main__':
    print("检查选择验证系统测试工具\n")
    
    try:
        # 显示案例统计
        show_case_statistics()
        
        # 运行验证测试
        test_validation_system()
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()