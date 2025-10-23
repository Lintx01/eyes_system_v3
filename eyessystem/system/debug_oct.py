#!/usr/bin/env python
"""
简单的OCT检查数据创建和调试脚本
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
import json

def debug_oct_data():
    """调试OCT检查数据"""
    
    print("=== 调试OCT检查数据 ===")
    
    # 查找所有检查选项
    all_exams = ExaminationOption.objects.all()
    print(f"总检查选项数量: {all_exams.count()}")
    
    # 查找OCT检查
    oct_exams = ExaminationOption.objects.filter(is_oct_exam=True)
    print(f"OCT检查数量: {oct_exams.count()}")
    
    if oct_exams.exists():
        for idx, oct_exam in enumerate(oct_exams, 1):
            print(f"\n--- OCT检查 #{idx} ---")
            print(f"ID: {oct_exam.id}")
            print(f"名称: {oct_exam.examination_name}")
            print(f"案例: {oct_exam.clinical_case.title}")
            print(f"是否OCT: {oct_exam.is_oct_exam}")
            print(f"图像显示模式: {oct_exam.image_display_mode}")
            
            # 检查各种图像字段
            print(f"\n图像字段检查:")
            print(f"- left_eye_image: {oct_exam.left_eye_image}")
            print(f"- right_eye_image: {oct_exam.right_eye_image}")
            print(f"- result_images: {oct_exam.result_images}")
            print(f"- additional_images: {oct_exam.additional_images}")
            
            # 检查OCT数据
            print(f"\nOCT数据:")
            print(f"- oct_measurement_data: {oct_exam.oct_measurement_data}")
            print(f"- oct_report_text: {oct_exam.oct_report_text[:100] if oct_exam.oct_report_text else None}...")
            print(f"- image_findings: {oct_exam.image_findings}")
    
    return oct_exams

def create_simple_oct_with_images():
    """创建带图像的简单OCT检查"""
    
    print("\n=== 创建简单OCT检查 ===")
    
    # 获取第一个案例
    case = ClinicalCase.objects.first()
    if not case:
        print("没有案例，先创建案例...")
        from django.contrib.auth.models import User
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username='admin', email='admin@test.com', password='admin123'
            )
        
        case = ClinicalCase.objects.create(
            case_id='TEST_OCT_001',
            title='OCT测试案例',
            patient_age=50,
            patient_gender='M',
            chief_complaint='视物模糊',
            present_illness='视物模糊2周',
            learning_objectives=['OCT检查'],
            created_by=admin_user
        )
        print(f"创建案例: {case.title}")
    
    # 删除现有OCT检查（如果有）
    ExaminationOption.objects.filter(
        clinical_case=case,
        examination_name__icontains='OCT'
    ).delete()
    
    # 创建新的OCT检查，使用result_images字段
    oct_exam = ExaminationOption.objects.create(
        clinical_case=case,
        examination_type='imaging',
        examination_name='OCT光学相干断层扫描',
        examination_description='OCT检查用于观察视网膜各层结构',
        normal_result='视网膜各层结构清晰，厚度正常',
        actual_result='黄斑区视网膜厚度增加，中心凹厚度420μm，可见微囊样水肿',
        diagnostic_value=3,
        cost_effectiveness=2,
        is_oct_exam=True,
        is_recommended=True,
        display_order=10,
        
        # 使用result_images字段（这个字段应该会被后端正确处理）
        result_images=[
            {
                'url': 'https://via.placeholder.com/400x300/e3f2fd/1565c0?text=OCT+Left+Eye',
                'description': '左眼OCT扫描',
                'eye': 'left'
            },
            {
                'url': 'https://via.placeholder.com/400x300/e8f5e8/2e7d32?text=OCT+Right+Eye', 
                'description': '右眼OCT扫描',
                'eye': 'right'
            }
        ],
        
        # OCT特殊数据
        oct_measurement_data={
            "central_thickness": "420μm",
            "average_thickness": "385μm", 
            "rnfl_superior": "95μm",
            "rnfl_inferior": "88μm",
            "rnfl_nasal": "78μm",
            "rnfl_temporal": "68μm"
        },
        
        oct_report_text='''OCT检查报告：
        
检查所见：
1. 黄斑区视网膜厚度明显增加，中心凹厚度420μm
2. 视网膜内可见多发微囊样低反射区
3. 视网膜色素上皮层基本连续
        
诊断意见：符合糖尿病性黄斑水肿表现''',
        
        image_display_mode='comparison',
        image_findings='黄斑区视网膜厚度增加，微囊样水肿明显'
    )
    
    print(f"创建OCT检查: {oct_exam.examination_name} (ID: {oct_exam.id})")
    print(f"图像数量: {len(oct_exam.result_images) if oct_exam.result_images else 0}")
    
    return oct_exam

def main():
    """主函数"""
    
    # 先调试现有数据
    existing_oct = debug_oct_data()
    
    # 如果没有OCT检查或数据不完整，创建新的
    if not existing_oct.exists() or not any(exam.result_images for exam in existing_oct):
        oct_exam = create_simple_oct_with_images()
        
        print(f"\n✅ OCT检查创建完成！")
        print(f"案例ID: {oct_exam.clinical_case.case_id}")
        print(f"检查ID: {oct_exam.id}")
        print(f"访问URL: /student/clinical/{oct_exam.clinical_case.case_id}/")
    else:
        print(f"\n✅ 现有OCT检查数据完整")
    
    print(f"\n请启动服务器测试:")
    print(f"python manage.py runserver")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ 出错: {e}")
        import traceback
        traceback.print_exc()