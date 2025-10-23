#!/usr/bin/env python
"""
OCT检查功能测试脚本
用于验证OCT检查的前端显示功能
"""

import os
import sys
import django
from pathlib import Path

# 添加Django项目路径
project_path = Path(__file__).parent
sys.path.insert(0, str(project_path))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption
from django.contrib.auth.models import User

def create_oct_test_data():
    """创建OCT检查的测试数据"""
    
    print("创建OCT检查测试数据...")
    
    # 获取或创建测试用户
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        print("创建管理员用户：admin/admin123")
    
    # 创建测试临床案例
    test_case, created = ClinicalCase.objects.get_or_create(
        case_id='OCT_TEST_001',
        defaults={
            'title': 'OCT检查测试案例 - 糖尿病视网膜病变',
            'patient_age': 58,
            'patient_gender': 'M',
            'chief_complaint': '视物模糊2周',
            'present_illness': '患者2周前开始出现双眼视物模糊，尤其是近距离视物困难，无眼痛、畏光等不适。',
            'past_history': '糖尿病病史10年，血糖控制欠佳。',
            'family_history': '父亲有糖尿病史。',
            'learning_objectives': ['掌握OCT检查的适应症', '理解OCT图像的解读', '学会分析OCT测量数据'],
            'difficulty_level': 'intermediate',
            'created_by': admin_user,
            'is_active': True
        }
    )
    
    if created:
        print(f"创建测试案例：{test_case.title}")
    else:
        print(f"使用现有案例：{test_case.title}")
    
    # 创建OCT检查选项
    oct_exam, oct_created = ExaminationOption.objects.get_or_create(
        clinical_case=test_case,
        examination_name='OCT光学相干断层扫描',
        defaults={
            'examination_type': 'imaging',
            'examination_description': 'OCT是一种非侵入性的影像检查技术，能够提供视网膜的高分辨率横截面图像，对于诊断黄斑疾病、青光眼等眼底疾病具有重要价值。',
            'normal_result': '视网膜各层结构清晰，厚度正常，无积液、出血等病理改变',
            'abnormal_result': '可见视网膜厚度异常、层间积液、视网膜色素上皮脱离等改变',
            'actual_result': '''OCT检查显示：
1. 黄斑区视网膜厚度增加，中心凹厚度约420μm（正常<250μm）
2. 视网膜内可见多发微囊样水肿
3. 视网膜色素上皮层连续性良好
4. 未见明显的视网膜色素上皮脱离
5. 玻璃体视网膜界面清晰，无牵拉''',
            'diagnostic_value': 3,
            'cost_effectiveness': 2,
            'is_oct_exam': True,
            'is_recommended': True,
            'display_order': 10,
            'oct_measurement_data': {
                "central_thickness": "420μm",
                "average_thickness": "385μm",
                "volume": "12.5mm³", 
                "rnfl_superior": "95μm",
                "rnfl_inferior": "88μm",
                "rnfl_nasal": "78μm",
                "rnfl_temporal": "68μm"
            },
            'oct_report_text': '''OCT检查报告：

检查部位：双眼黄斑区
检查日期：2024年10月22日

检查所见：
1. 黄斑区视网膜厚度明显增加，中心凹厚度420μm，远超正常值上限
2. 视网膜内可见多发微囊样低反射区，提示视网膜水肿
3. 外核层和外丛状层边界模糊
4. 视网膜色素上皮层基本连续，反射增强
5. 脉络膜厚度正常，约280μm

诊断意见：
符合糖尿病性黄斑水肿的OCT表现，建议结合眼底照片和荧光造影进一步评估。

建议：
1. 严格控制血糖
2. 考虑抗VEGF治疗
3. 定期OCT随访观察''',
            'image_display_mode': 'comparison',
            'image_findings': '黄斑区视网膜厚度增加，可见微囊样水肿，外核层边界模糊',
            'additional_images': [
                {
                    'url': '/media/examination_images/oct_samples/oct_diabetic_left.jpg',
                    'description': '左眼OCT黄斑区扫描',
                    'eye': 'left',
                    'findings': '视网膜厚度增加，微囊样水肿明显'
                },
                {
                    'url': '/media/examination_images/oct_samples/oct_diabetic_right.jpg', 
                    'description': '右眼OCT黄斑区扫描',
                    'eye': 'right',
                    'findings': '视网膜厚度增加，水肿程度较左眼轻'
                }
            ]
        }
    )
    
    if oct_created:
        print(f"创建OCT检查：{oct_exam.examination_name}")
    else:
        print(f"使用现有OCT检查：{oct_exam.examination_name}")
    
    print("\nOCT检查测试数据创建完成！")
    print(f"案例ID: {test_case.case_id}")
    print(f"检查ID: {oct_exam.id}")
    print("\n您现在可以通过以下方式测试OCT功能：")
    print("1. 启动开发服务器：python manage.py runserver")
    print("2. 访问临床推理系统")
    print("3. 选择检查项目时选择'OCT光学相干断层扫描'")
    print("4. 查看检查结果时观察OCT特殊显示效果")

if __name__ == '__main__':
    create_oct_test_data()