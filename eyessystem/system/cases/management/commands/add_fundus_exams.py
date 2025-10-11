"""
Django管理命令：为现有临床案例添加眼底检查项目
使用方法：python manage.py add_fundus_exams
"""

from django.core.management.base import BaseCommand
from cases.models import ClinicalCase, ExaminationOption
import json


class Command(BaseCommand):
    help = '为现有临床案例添加眼底检查项目，测试新功能'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始添加眼底检查项目...'))

        # 为所有现有案例添加眼底检查
        cases = ClinicalCase.objects.filter(is_active=True)
        
        for case in cases:
            self.add_fundus_examinations(case)
            
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== 眼底检查项目添加完成！===\n'
                f'已为 {cases.count()} 个案例添加眼底检查项目\n'
                '现在可以测试以下功能：\n'
                '1. 眼底检查的大字提示\n'
                '2. 必选检查验证\n'
                '3. 检查图像展示\n'
                '访问地址：http://127.0.0.1:8000/student/clinical-cases/\n'
            )
        )

    def add_fundus_examinations(self, clinical_case):
        """为指定案例添加眼底检查项目"""
        
        # 检查是否已经有眼底检查项目
        existing_fundus = ExaminationOption.objects.filter(
            clinical_case=clinical_case,
            examination_type='fundus'
        ).exists()
        
        if existing_fundus:
            self.stdout.write(f'- 案例 {clinical_case.case_id} 已有眼底检查项目')
            return

        # 根据不同案例添加相应的眼底检查项目
        if clinical_case.case_id == 'CASE_001':  # 糖尿病性黄斑水肿
            fundus_exams = [
                {
                    'name': '直接眼底镜检查',
                    'description': '使用直接眼底镜观察视网膜和视盘',
                    'result': '黄斑区可见硬性渗出和微出血点，视盘边界清楚，血管稍变细',
                    'is_required': True,
                    'is_fundus_exam': True,
                    'diagnostic_value': 3,
                    'images': [
                        '/static/images/case001_fundus_direct.jpg',
                        '/static/images/case001_fundus_macula.jpg'
                    ]
                },
                {
                    'name': '间接眼底镜检查',
                    'description': '使用间接眼底镜进行全面眼底检查',
                    'result': '周边视网膜可见散在微动脉瘤和点状出血，黄斑区水肿明显',
                    'is_required': False,
                    'is_fundus_exam': True,
                    'diagnostic_value': 2,
                    'images': [
                        '/static/images/case001_fundus_indirect.jpg'
                    ]
                },
                {
                    'name': '眼底照相',
                    'description': '数字眼底照相记录病变',
                    'result': '彩色眼底照片显示典型糖尿病视网膜病变表现',
                    'is_required': False,
                    'is_fundus_exam': True,
                    'diagnostic_value': 3,
                    'images': [
                        '/static/images/case001_fundus_photo.jpg',
                        '/static/images/case001_fundus_color.jpg'
                    ]
                }
            ]
        elif clinical_case.case_id == 'CASE_002':  # 急性闭角型青光眼
            fundus_exams = [
                {
                    'name': '直接眼底镜检查',
                    'description': '检查视盘和视网膜血管',
                    'result': '视盘充血水肿，杯盘比增大，静脉充盈',
                    'is_required': True,
                    'is_fundus_exam': True,
                    'diagnostic_value': 3,
                    'images': [
                        '/static/images/case002_fundus_disc.jpg'
                    ]
                },
                {
                    'name': '眼底照相',
                    'description': '记录视盘和血管变化',
                    'result': '视盘水肿，血管迂曲，可见视网膜水肿',
                    'is_required': False,
                    'is_fundus_exam': True,
                    'diagnostic_value': 2,
                    'images': [
                        '/static/images/case002_fundus_photo.jpg'
                    ]
                }
            ]
        else:
            # 通用眼底检查
            fundus_exams = [
                {
                    'name': '直接眼底镜检查',
                    'description': '基础眼底检查',
                    'result': '根据具体病例确定检查结果',
                    'is_required': True,
                    'is_fundus_exam': True,
                    'diagnostic_value': 3,
                    'images': []
                }
            ]

        # 创建眼底检查项目
        for exam_data in fundus_exams:
            ExaminationOption.objects.create(
                clinical_case=clinical_case,
                examination_type='fundus',
                examination_name=exam_data['name'],
                examination_description=exam_data['description'],
                normal_result='视盘边界清楚，血管正常，黄斑区无异常',
                abnormal_result='存在病理性改变',
                actual_result=exam_data['result'],
                diagnostic_value=exam_data['diagnostic_value'],
                cost_effectiveness=2,
                result_images=exam_data.get('images', []),
                is_required=exam_data.get('is_required', False),
                is_multiple_choice=False,
                is_fundus_exam=exam_data.get('is_fundus_exam', True),
                fundus_reminder_text='请移步旁边进行观察',
                is_recommended=True,
                display_order=100  # 放在后面显示
            )

        # 同时添加一些其他检查项目作为对比
        other_exams = [
            {
                'type': 'basic',
                'name': '视力检查',
                'description': '测量最佳矫正视力',
                'result': '右眼视力0.3，左眼视力0.4',
                'is_required': True,
                'diagnostic_value': 2
            },
            {
                'type': 'basic',
                'name': '眼压测量',
                'description': '使用眼压计测量眼内压',
                'result': '右眼15mmHg，左眼16mmHg' if clinical_case.case_id == 'CASE_001' else '右眼45mmHg，左眼18mmHg',
                'is_required': clinical_case.case_id == 'CASE_002',  # 青光眼案例必须测眼压
                'diagnostic_value': 3 if clinical_case.case_id == 'CASE_002' else 2
            },
            {
                'type': 'imaging',
                'name': 'OCT检查',
                'description': '光学相干断层扫描',
                'result': '黄斑区囊样水肿，中心凹厚度增加' if clinical_case.case_id == 'CASE_001' else '视盘周围神经纤维层变薄',
                'is_required': False,
                'diagnostic_value': 3,
                'images': ['/static/images/oct_sample.jpg']
            }
        ]

        for exam_data in other_exams:
            # 检查是否已存在相同名称的检查
            if ExaminationOption.objects.filter(
                clinical_case=clinical_case,
                examination_name=exam_data['name']
            ).exists():
                continue
                
            ExaminationOption.objects.create(
                clinical_case=clinical_case,
                examination_type=exam_data['type'],
                examination_name=exam_data['name'],
                examination_description=exam_data['description'],
                normal_result='正常范围内',
                abnormal_result='存在异常',
                actual_result=exam_data['result'],
                diagnostic_value=exam_data['diagnostic_value'],
                cost_effectiveness=2,
                result_images=exam_data.get('images', []),
                is_required=exam_data.get('is_required', False),
                is_multiple_choice=False,
                is_fundus_exam=False,
                is_recommended=True,
                display_order=50
            )

        self.stdout.write(f'✓ 为案例 {clinical_case.case_id} 添加了眼底检查项目')