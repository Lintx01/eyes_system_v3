#!/usr/bin/env python
"""
检查OCT字段是否正确添加到数据库
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
project_path = Path(__file__).parent
sys.path.insert(0, str(project_path))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ExaminationOption

def check_oct_fields():
    """检查OCT相关字段是否存在"""
    
    print("检查ExaminationOption模型的OCT相关字段...")
    
    # 获取模型的字段列表
    fields = ExaminationOption._meta.get_fields()
    field_names = [field.name for field in fields]
    
    oct_fields = [
        'is_oct_exam',
        'oct_report_text', 
        'oct_measurement_data',
        'image_display_mode',
        'image_annotations',
        'image_findings',
        'additional_images'
    ]
    
    print(f"模型总字段数: {len(field_names)}")
    print("\n检查OCT相关字段:")
    
    for field in oct_fields:
        if field in field_names:
            print(f"✓ {field} - 存在")
        else:
            print(f"✗ {field} - 缺失")
    
    print(f"\n所有字段列表:")
    for i, field in enumerate(field_names, 1):
        print(f"{i:2d}. {field}")
    
    # 检查是否有现有的检查选项
    exam_count = ExaminationOption.objects.count()
    print(f"\n当前数据库中的检查选项数量: {exam_count}")
    
    if exam_count > 0:
        # 显示第一个检查选项的信息
        first_exam = ExaminationOption.objects.first()
        print(f"第一个检查选项: {first_exam.examination_name}")
        print(f"是否OCT检查: {getattr(first_exam, 'is_oct_exam', '字段不存在')}")

if __name__ == '__main__':
    check_oct_fields()