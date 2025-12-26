#!/usr/bin/env python
"""
检查病例数据的脚本
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase

# 获取病例 CCC7D361F8
case_id = 'CCC7D361F8'
try:
    case = ClinicalCase.objects.get(case_id=case_id)
    print(f"\n{'='*60}")
    print(f"病例编号: {case.case_id}")
    print(f"病例标题: {case.title}")
    print(f"{'='*60}\n")
    
    print(f"患者信息:")
    print(f"  年龄: {case.patient_age}岁")
    print(f"  性别: {case.get_patient_gender_display()}")
    print()
    
    print(f"主诉:")
    print(f"  {case.chief_complaint}")
    print()
    
    print(f"现病史:")
    print(f"  {case.present_illness}")
    print()
    
    print(f"既往史:")
    print(f"  {case.past_history if case.past_history else '（无）'}")
    print()
    
    print(f"家族史:")
    print(f"  {case.family_history if case.family_history else '（无）'}")
    print()
    
except ClinicalCase.DoesNotExist:
    print(f"错误: 病例 {case_id} 不存在！")
    print("\n可用的病例:")
    for case in ClinicalCase.objects.all()[:5]:
        print(f"  - {case.case_id}: {case.title}")
