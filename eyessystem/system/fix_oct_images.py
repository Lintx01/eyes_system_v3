#!/usr/bin/env python
"""
修复OCT检查图像显示问题的脚本
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

from cases.models import ExaminationOption, ClinicalCase
from django.core.files import File
from PIL import Image
import io

def create_sample_images():
    """创建示例图像"""
    
    # 创建一个简单的示例图像
    def create_placeholder_image(text, width=400, height=300):
        """创建占位符图像"""
        img = Image.new('RGB', (width, height), color='lightgray')
        
        # 保存到内存
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        return img_io
    
    # 确保媒体目录存在
    media_dir = Path('media/examination_images')
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建示例图像文件
    oct_left_path = media_dir / 'oct_left_sample.png'
    oct_right_path = media_dir / 'oct_right_sample.png'
    
    if not oct_left_path.exists():
        left_img = create_placeholder_image('OCT Left Eye', 400, 300)
        with open(oct_left_path, 'wb') as f:
            f.write(left_img.read())
        print(f"创建示例图像: {oct_left_path}")
    
    if not oct_right_path.exists():
        right_img = create_placeholder_image('OCT Right Eye', 400, 300)
        with open(oct_right_path, 'wb') as f:
            f.write(right_img.read())
        print(f"创建示例图像: {oct_right_path}")
    
    return oct_left_path, oct_right_path

def fix_oct_images():
    """修复OCT检查的图像显示问题"""
    
    print("=== 修复OCT图像显示问题 ===")
    
    # 创建示例图像
    oct_left_path, oct_right_path = create_sample_images()
    
    # 查找OCT检查选项
    oct_exams = ExaminationOption.objects.filter(is_oct_exam=True)
    
    if not oct_exams.exists():
        print("未找到OCT检查选项，创建新的OCT检查...")
        
        # 获取第一个案例
        case = ClinicalCase.objects.first()
        if not case:
            print("没有找到临床案例，请先创建案例")
            return
        
        # 创建OCT检查
        oct_exam = ExaminationOption.objects.create(
            clinical_case=case,
            examination_type='imaging',
            examination_name='OCT光学相干断层扫描',
            examination_description='OCT检查用于观察视网膜各层结构',
            normal_result='视网膜各层结构清晰',
            actual_result='黄斑区视网膜厚度增加，可见微囊样水肿',
            diagnostic_value=3,
            cost_effectiveness=2,
            is_oct_exam=True,
            is_recommended=True,
            display_order=10,
            oct_measurement_data={
                "central_thickness": "420μm",
                "average_thickness": "385μm",
                "rnfl_superior": "95μm",
                "rnfl_inferior": "88μm"
            },
            oct_report_text='OCT检查显示黄斑区视网膜厚度增加',
            image_display_mode='comparison',
            image_findings='黄斑区视网膜厚度增加，微囊样水肿明显'
        )
        oct_exams = [oct_exam]
    
    # 更新OCT检查的图像和additional_images字段
    for oct_exam in oct_exams:
        print(f"更新OCT检查: {oct_exam.examination_name}")
        
        # 更新additional_images字段以包含示例图像
        oct_exam.additional_images = [
            {
                'url': '/media/examination_images/oct_left_sample.png',
                'description': '左眼OCT黄斑区扫描',
                'eye': 'left',
                'findings': '视网膜厚度增加，微囊样水肿明显'
            },
            {
                'url': '/media/examination_images/oct_right_sample.png',
                'description': '右眼OCT黄斑区扫描', 
                'eye': 'right',
                'findings': '视网膜厚度增加，水肿程度较左眼轻'
            }
        ]
        
        # 同时更新result_images字段
        oct_exam.result_images = [
            '/media/examination_images/oct_left_sample.png',
            '/media/examination_images/oct_right_sample.png'
        ]
        
        oct_exam.save()
        print(f"✅ 更新完成，图像数量: {len(oct_exam.additional_images)}")
    
    print("\n=== 验证数据 ===")
    for oct_exam in oct_exams:
        print(f"检查ID: {oct_exam.id}")
        print(f"是否OCT: {oct_exam.is_oct_exam}")
        print(f"Additional Images: {oct_exam.additional_images}")
        print(f"Result Images: {oct_exam.result_images}")
        print("-" * 50)
    
    print("\n✅ OCT图像显示问题修复完成！")
    print("现在启动服务器测试图像显示:")
    print("python manage.py runserver")

if __name__ == '__main__':
    try:
        fix_oct_images()
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        import traceback
        traceback.print_exc()