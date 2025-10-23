#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试新的检查选项API - 必选项 + 干扰项系统
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption
import json


def test_examination_options_logic():
    """测试检查选项逻辑"""
    print("=== 测试检查选项API逻辑 ===\n")
    
    # 1. 检查现有案例
    print("1. 查看现有案例:")
    cases = ClinicalCase.objects.filter(is_active=True)
    for case in cases:
        print(f"   案例ID: {case.case_id}, 标题: {case.title}")
        required_exams = ExaminationOption.objects.filter(
            clinical_case=case, is_required=True
        ).count()
        total_exams = ExaminationOption.objects.filter(clinical_case=case).count()
        print(f"   必选检查: {required_exams}, 总检查项: {total_exams}")
    
    print()
    
    # 2. 检查干扰项池
    print("2. 检查干扰项池:")
    try:
        distractor_case = ClinicalCase.objects.get(case_id='DISTRACTOR_POOL')
        distractor_count = ExaminationOption.objects.filter(clinical_case=distractor_case).count()
        print(f"   干扰项池案例: {distractor_case.title}")
        print(f"   干扰项总数: {distractor_count}")
    except ClinicalCase.DoesNotExist:
        print("   干扰项池不存在，需要创建")
        return False
    
    print()
    
    # 3. 模拟API逻辑（不实际调用视图函数，而是复制逻辑）
    print("3. 模拟新API逻辑:")
    if cases.exists():
        test_case = cases.first()
        print(f"   测试案例: {test_case.title}")
        
        # 获取必选检查项
        required_examinations = ExaminationOption.objects.filter(
            clinical_case=test_case,
            is_required=True
        )
        print(f"   必选检查项: {required_examinations.count()}")
        for exam in required_examinations:
            print(f"     - {exam.examination_name} ({exam.get_examination_type_display()})")
        
        # 获取干扰项池
        distractor_pool = ExaminationOption.objects.exclude(
            clinical_case=test_case
        ).filter(
            is_required=False
        )
        print(f"   可用干扰项: {distractor_pool.count()}")
        
        # 按类型分组
        distractor_by_type = {}
        for exam in distractor_pool:
            exam_type = exam.examination_type
            if exam_type not in distractor_by_type:
                distractor_by_type[exam_type] = []
            distractor_by_type[exam_type].append(exam)
        
        print("   干扰项分类:")
        for exam_type, exams in distractor_by_type.items():
            print(f"     {exam_type}: {len(exams)} 项")
    
    return True


def create_sample_distractor_pool():
    """创建示例干扰项池"""
    print("=== 创建示例干扰项池 ===\n")
    
    # 创建干扰项池案例
    distractor_case, created = ClinicalCase.objects.get_or_create(
        case_id='DISTRACTOR_POOL',
        defaults={
            'title': '通用检查项目池（系统用）',
            'description': '用于生成干扰项的通用检查项目池',
            'difficulty_level': 'intermediate',
            'target_diagnosis': '系统用途',
            'is_active': False,
            'created_by_id': 1
        }
    )
    
    if created:
        print(f"创建干扰项池案例: {distractor_case.title}")
    else:
        print(f"干扰项池案例已存在: {distractor_case.title}")
    
    # 创建一些示例干扰项
    sample_distractors = [
        {
            'examination_name': '血常规检查',
            'examination_type': 'laboratory',
            'examination_description': '检查血液中各种细胞成分',
            'diagnostic_value': 'low',
            'cost_effectiveness': 'high',
        },
        {
            'examination_name': '色觉检查',
            'examination_type': 'functional',
            'examination_description': '检查患者对颜色的识别能力',
            'diagnostic_value': 'low',
            'cost_effectiveness': 'high',
        },
        {
            'examination_name': '头部CT检查',
            'examination_type': 'imaging',
            'examination_description': '检查头部结构',
            'diagnostic_value': 'medium',
            'cost_effectiveness': 'low',
        },
        {
            'examination_name': '泪液分泌试验',
            'examination_type': 'functional',
            'examination_description': '评估泪腺分泌功能',
            'diagnostic_value': 'medium',
            'cost_effectiveness': 'high',
        },
    ]
    
    created_count = 0
    for exam_data in sample_distractors:
        examination, created = ExaminationOption.objects.get_or_create(
            clinical_case=distractor_case,
            examination_name=exam_data['examination_name'],
            defaults={
                **exam_data,
                'is_recommended': False,
                'is_required': False
            }
        )
        
        if created:
            created_count += 1
            print(f"创建干扰项: {examination.examination_name}")
    
    print(f"新创建 {created_count} 个干扰项")
    return distractor_case


if __name__ == '__main__':
    # 先创建示例干扰项池
    create_sample_distractor_pool()
    print()
    
    # 然后测试逻辑
    test_examination_options_logic()