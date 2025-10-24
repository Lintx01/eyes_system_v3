#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为案例添加错误诊断选项以测试智能指导系统
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import DiagnosisOption, ClinicalCase


def add_wrong_diagnosis_options():
    """为案例添加错误诊断选项"""
    
    print("=== 添加错误诊断选项 ===\n")
    
    # 获取案例
    case = ClinicalCase.objects.first()
    if not case:
        print("❌ 没有找到案例")
        return
        
    print(f"📋 案例: {case.case_id} - {case.title}")
    
    # 检查现有选项
    existing_options = DiagnosisOption.objects.filter(clinical_case=case)
    print(f"现有诊断选项 ({existing_options.count()}个):")
    for opt in existing_options:
        print(f"  - {opt.diagnosis_name}: 正确={opt.is_correct_diagnosis}")
    
    # 定义错误诊断选项（干扰项）
    wrong_diagnoses = [
        {
            'diagnosis_name': '青光眼',
            'diagnosis_code': 'H40.9',
            'supporting_evidence': '青光眼通常表现为眼压升高、视野缺损',
            'contradicting_evidence': '该患者眼压正常，视野缺损模式不符合青光眼',
            'typical_symptoms': ['眼痛', '视力下降', '视野缺损'],
            'typical_signs': ['眼压升高', '视盘凹陷', '角膜水肿'],
            'correct_feedback': '诊断正确',
            'incorrect_feedback': '该患者眼压正常，无青光眼特征性改变',
            'hint_level_1': '注意患者的眼压值和视野缺损情况',
            'hint_level_2': '高眼压(>21mmHg)、视野缺损和视盘凹陷是青光眼的重要指标',
            'hint_level_3': '该患者眼压正常，视野缺损模式与青光眼不符，不支持青光眼诊断',
            'probability_score': 0.1,
            'display_order': 4
        },
        {
            'diagnosis_name': '白内障',
            'diagnosis_code': 'H25.9',
            'supporting_evidence': '白内障主要表现为晶状体混浊导致的视力下降',
            'contradicting_evidence': '该患者主要问题在于视网膜病变，非晶状体问题',
            'typical_symptoms': ['视力逐渐下降', '眩光', '复视'],
            'typical_signs': ['晶状体混浊', '红光反射异常'],
            'correct_feedback': '诊断正确',
            'incorrect_feedback': '该患者主要表现为视网膜病变，晶状体透明',
            'hint_level_1': '观察晶状体的透明度变化',
            'hint_level_2': '晶状体混浊导致视力下降是白内障的主要特征',
            'hint_level_3': '该患者晶状体透明，视力下降主要由视网膜病变引起，不符合白内障',
            'probability_score': 0.05,
            'display_order': 5
        },
        {
            'diagnosis_name': '黄斑变性',
            'diagnosis_code': 'H35.3',
            'supporting_evidence': '黄斑变性表现为中心视力下降，黄斑区异常',
            'contradicting_evidence': '该患者主要为血管性病变，非黄斑退行性改变',
            'typical_symptoms': ['中心视力下降', '视物变形', '中心暗点'],
            'typical_signs': ['黄斑区色素紊乱', '玻璃膜疣', '地图样萎缩'],
            'correct_feedback': '诊断正确',
            'incorrect_feedback': '该患者主要为血管性改变，非黄斑退行性病变',
            'hint_level_1': '注意患者的中心视力和黄斑区变化',
            'hint_level_2': '黄斑区色素紊乱、玻璃膜疣和地图样萎缩是黄斑变性的特征',
            'hint_level_3': '该患者病变主要为血管性，黄斑区无典型的退行性改变，不支持黄斑变性诊断',
            'probability_score': 0.15,
            'display_order': 6
        }
    ]
    
    # 添加错误诊断选项
    added_count = 0
    for wrong_diagnosis in wrong_diagnoses:
        # 检查是否已存在
        if not DiagnosisOption.objects.filter(
            clinical_case=case, 
            diagnosis_name=wrong_diagnosis['diagnosis_name']
        ).exists():
            
            DiagnosisOption.objects.create(
                clinical_case=case,
                is_correct_diagnosis=False,  # 设置为错误诊断
                is_differential=True,
                **wrong_diagnosis
            )
            added_count += 1
            print(f"✅ 已添加错误诊断选项: {wrong_diagnosis['diagnosis_name']}")
        else:
            print(f"○ 诊断选项已存在: {wrong_diagnosis['diagnosis_name']}")
    
    # 确保至少有一个正确诊断不是必须全选的
    correct_options = existing_options.filter(is_correct_diagnosis=True)
    if correct_options.count() > 2:
        # 将第三个正确诊断改为可选的
        third_correct = correct_options[2]
        third_correct.is_correct_diagnosis = False
        third_correct.probability_score = 0.7  # 设置为较高概率但非必需
        third_correct.save()
        print(f"🔄 已将 '{third_correct.diagnosis_name}' 调整为干扰选项（高概率但非必需）")
    
    # 显示最终结果
    print(f"\n📊 最终诊断选项配置:")
    all_options = DiagnosisOption.objects.filter(clinical_case=case).order_by('display_order')
    correct_count = 0
    wrong_count = 0
    
    for opt in all_options:
        status = "✅ 正确" if opt.is_correct_diagnosis else "❌ 错误"
        print(f"  - {opt.diagnosis_name}: {status} (概率: {opt.probability_score})")
        if opt.is_correct_diagnosis:
            correct_count += 1
        else:
            wrong_count += 1
    
    print(f"\n🎯 配置完成:")
    print(f"  正确诊断: {correct_count} 个")
    print(f"  错误选项: {wrong_count} 个")
    print(f"  新增选项: {added_count} 个")
    
    print(f"\n✨ 智能指导系统现在可以正常测试了！")
    print("学生如果选择错误诊断，将收到循序渐进的指导。")


if __name__ == '__main__':
    add_wrong_diagnosis_options()