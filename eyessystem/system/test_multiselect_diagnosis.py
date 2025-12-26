#!/usr/bin/env python
"""
测试多选诊断功能
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, DiagnosisOption

def test_multiselect_cases():
    """检查哪些病例有多选诊断"""
    print("=" * 80)
    print("检查所有病例的正确诊断数量")
    print("=" * 80)
    
    cases = ClinicalCase.objects.filter(is_active=True)
    
    for case in cases:
        correct_options = DiagnosisOption.objects.filter(
            clinical_case=case,
            is_correct_diagnosis=True
        )
        
        print(f"\n病例 ID={case.case_id}: {case.case_title}")
        print(f"  正确诊断数量: {correct_options.count()}")
        
        if correct_options.count() > 1:
            print(f"  ⚠️ 这是一个多选病例！")
            for opt in correct_options:
                print(f"    - ID={opt.id}: {opt.diagnosis_name}")
        elif correct_options.count() == 1:
            opt = correct_options.first()
            print(f"  ✓ 单选病例: ID={opt.id}: {opt.diagnosis_name}")
        else:
            print(f"  ❌ 警告：没有设置正确诊断！")

def test_diagnosis_scoring():
    """测试诊断评分逻辑"""
    print("\n" + "=" * 80)
    print("测试诊断评分逻辑")
    print("=" * 80)
    
    # 测试场景
    test_scenarios = [
        {
            'name': '完全正确（单选）',
            'correct_ids': {16},
            'selected_ids': {16},
            'expected_score': 100
        },
        {
            'name': '完全正确（多选）',
            'correct_ids': {11, 12},
            'selected_ids': {11, 12},
            'expected_score': 100
        },
        {
            'name': '部分正确（选少了）',
            'correct_ids': {11, 12},
            'selected_ids': {11},
            'expected_score': 66.67  # precision=1.0, recall=0.5, F1=0.667
        },
        {
            'name': '部分正确（选多了）',
            'correct_ids': {11, 12},
            'selected_ids': {11, 12, 13},
            'expected_score': 80.0  # precision=0.667, recall=1.0, F1=0.8
        },
        {
            'name': '完全错误',
            'correct_ids': {11, 12},
            'selected_ids': {13, 14},
            'expected_score': 0
        },
    ]
    
    for scenario in test_scenarios:
        correct = scenario['correct_ids']
        selected = scenario['selected_ids']
        
        correctly_selected = len(selected & correct)
        incorrectly_selected = len(selected - correct)
        missed = len(correct - selected)
        
        # 计算分数
        if missed == 0 and incorrectly_selected == 0:
            score = 100
        else:
            precision = correctly_selected / len(selected) if selected else 0
            recall = correctly_selected / len(correct)
            if precision + recall > 0:
                f1_score = 2 * (precision * recall) / (precision + recall)
                score = f1_score * 100
            else:
                score = 0
        
        print(f"\n场景: {scenario['name']}")
        print(f"  正确答案: {correct}")
        print(f"  学生选择: {selected}")
        print(f"  正确选中: {correctly_selected}")
        print(f"  错误选中: {incorrectly_selected}")
        print(f"  遗漏: {missed}")
        print(f"  得分: {score:.2f} (期望: {scenario['expected_score']})")
        
        # 验证
        if abs(score - scenario['expected_score']) < 1:
            print(f"  ✓ 通过")
        else:
            print(f"  ❌ 失败")

if __name__ == '__main__':
    test_multiselect_cases()
    test_diagnosis_scoring()
