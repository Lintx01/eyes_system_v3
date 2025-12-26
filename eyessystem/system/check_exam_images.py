#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查检查选项表中的图片字段数据"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ExaminationOption

def check_examination_images():
    """检查所有检查选项的图片字段"""
    exams = ExaminationOption.objects.all()
    
    print(f"总检查选项数: {exams.count()}\n")
    print("=" * 80)
    
    has_images = 0
    no_images = 0
    
    for exam in exams:
        has_any_image = False
        
        print(f"\nID: {exam.id}")
        print(f"名称: {exam.examination_name}")
        print(f"类型: {exam.examination_type}")
        print(f"所属病例: {exam.clinical_case.chief_complaint if exam.clinical_case else 'None'}")
        
        # 检查各种图片字段
        if exam.result_images:
            print(f"  ✓ result_images: {exam.result_images}")
            has_any_image = True
        else:
            print(f"  ✗ result_images: 空")
            
        if exam.left_eye_image:
            print(f"  ✓ left_eye_image: {exam.left_eye_image}")
            has_any_image = True
        else:
            print(f"  ✗ left_eye_image: 空")
            
        if exam.right_eye_image:
            print(f"  ✓ right_eye_image: {exam.right_eye_image}")
            has_any_image = True
        else:
            print(f"  ✗ right_eye_image: 空")
            
        if exam.additional_images:
            print(f"  ✓ additional_images: {exam.additional_images}")
            has_any_image = True
        else:
            print(f"  ✗ additional_images: 空")
        
        if has_any_image:
            has_images += 1
        else:
            no_images += 1
            
        print("-" * 80)
    
    print(f"\n统计:")
    print(f"  有图片的检查选项: {has_images}")
    print(f"  无图片的检查选项: {no_images}")
    print(f"  图片覆盖率: {has_images/exams.count()*100:.1f}%")

if __name__ == '__main__':
    check_examination_images()
