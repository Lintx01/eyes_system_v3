#!/usr/bin/env python
"""
创建超级用户和OCT测试数据的简化脚本
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

from django.contrib.auth.models import User
from cases.models import ClinicalCase, ExaminationOption

def create_test_data():
    """创建测试数据"""
    
    print("=== 创建OCT测试数据 ===")
    
    # 1. 创建超级用户（如果不存在）
    try:
        admin_user = User.objects.get(username='admin')
        print(f"使用现有管理员用户: {admin_user.username}")
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com', 
            password='admin123'
        )
        print("创建新管理员用户: admin/admin123")
    
    # 2. 创建临床案例（如果不存在）
    case, created = ClinicalCase.objects.get_or_create(
        case_id='OCT_TEST_CASE',
        defaults={
            'title': 'OCT检查测试案例',
            'patient_age': 58,
            'patient_gender': 'M',
            'chief_complaint': '视物模糊2周',
            'present_illness': '患者2周前开始出现双眼视物模糊，尤其是近距离视物困难。',
            'past_history': '糖尿病病史10年。',
            'family_history': '无特殊家族史。',
            'learning_objectives': ['学习OCT检查', '掌握OCT图像解读'],
            'difficulty_level': 'intermediate',
            'created_by': admin_user,
            'is_active': True
        }
    )
    
    if created:
        print(f"创建新临床案例: {case.title}")
    else:
        print(f"使用现有案例: {case.title}")
    
    # 3. 创建OCT检查选项
    oct_exam, oct_created = ExaminationOption.objects.get_or_create(
        clinical_case=case,
        examination_name='OCT光学相干断层扫描',
        defaults={
            'examination_type': 'imaging',
            'examination_description': 'OCT检查用于观察视网膜各层结构，是眼底疾病诊断的重要工具。',
            'normal_result': '视网膜各层结构清晰，厚度正常。',
            'actual_result': '黄斑区视网膜厚度增加，可见微囊样水肿。',
            'diagnostic_value': 3,
            'cost_effectiveness': 2,
            'is_oct_exam': True,
            'is_recommended': True,
            'display_order': 10,
            'oct_measurement_data': {
                "central_thickness": "420μm",
                "average_thickness": "385μm",
                "rnfl_superior": "95μm",
                "rnfl_inferior": "88μm"
            },
            'oct_report_text': 'OCT检查显示黄斑区视网膜厚度增加，符合糖尿病性黄斑水肿表现。',
            'image_display_mode': 'comparison',
            'image_findings': '黄斑区视网膜厚度增加，微囊样水肿明显'
        }
    )
    
    if oct_created:
        print(f"创建OCT检查: {oct_exam.examination_name}")
    else:
        print(f"使用现有OCT检查: {oct_exam.examination_name}")
    
    # 4. 验证数据
    print("\n=== 验证创建的数据 ===")
    print(f"临床案例ID: {case.case_id}")
    print(f"OCT检查ID: {oct_exam.id}")
    print(f"是否OCT检查: {oct_exam.is_oct_exam}")
    print(f"OCT测量数据: {oct_exam.oct_measurement_data}")
    
    print("\n✅ OCT测试数据创建完成！")
    print("现在可以启动服务器测试OCT功能了:")
    print("python manage.py runserver")

if __name__ == '__main__':
    try:
        create_test_data()
    except Exception as e:
        print(f"❌ 创建数据时出错: {e}")
        import traceback
        traceback.print_exc()