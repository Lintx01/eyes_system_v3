"""
Django管理命令：初始化临床推理系统示例数据
使用方法：python manage.py init_clinical_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from cases.models import (
    ClinicalCase, ExaminationOption, DiagnosisOption, 
    TreatmentOption, StudentClinicalSession, TeachingFeedback
)
import json


class Command(BaseCommand):
    help = '初始化临床推理系统的示例案例数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有临床推理数据',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化临床推理示例数据...'))

        # 如果指定了清除选项，先清除现有数据
        if options['clear']:
            self.stdout.write('清除现有临床推理数据...')
            StudentClinicalSession.objects.all().delete()
            TeachingFeedback.objects.all().delete()
            TreatmentOption.objects.all().delete()
            DiagnosisOption.objects.all().delete()
            ExaminationOption.objects.all().delete()
            ClinicalCase.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ 现有数据已清除'))

        # 示例数据
        clinical_cases_data = [
            {
                "id": 1,
                "title": "糖尿病性黄斑水肿",
                "chief_complaint": "视力下降2周",
                "present_history": "患者男性，58岁，双眼视力逐渐下降2周，无眼痛。既往有糖尿病10年，血糖控制不佳。",
                "past_history": "糖尿病10年，高血压5年，无青光眼史。",
                "examinations": [
                    {
                        "name": "视力检查",
                        "result": "右眼0.3，左眼0.4，矫正无明显改善。",
                        "weight": 0.2
                    },
                    {
                        "name": "眼压测量",
                        "result": "双眼眼压均正常（15 mmHg）。",
                        "weight": 0.1
                    },
                    {
                        "name": "裂隙灯检查",
                        "result": "角膜透明，晶状体轻度混浊。",
                        "weight": 0.1
                    },
                    {
                        "name": "OCT",
                        "result": "黄斑区囊样水肿伴反射信号减弱。",
                        "weight": 0.4
                    },
                    {
                        "name": "眼底检查",
                        "result": "提示需实体设备完成。",
                        "virtual": False,
                        "weight": 0
                    }
                ],
                "differential_diagnoses": [
                    {
                        "option": "糖尿病性黄斑水肿",
                        "is_correct": True,
                        "explanation": "OCT提示囊样水肿，结合糖尿病史，是典型表现。"
                    },
                    {
                        "option": "黄斑前膜",
                        "is_correct": False,
                        "explanation": "OCT未见表面反光膜样结构，不支持。"
                    },
                    {
                        "option": "视神经萎缩",
                        "is_correct": False,
                        "explanation": "视盘颜色及边界正常，不支持此诊断。"
                    },
                    {
                        "option": "黄斑裂孔",
                        "is_correct": False,
                        "explanation": "未见全层裂孔征象，不符。"
                    }
                ],
                "treatments": [
                    {
                        "option": "玻璃体腔注射抗VEGF药物",
                        "is_recommended": True,
                        "reason": "糖尿病黄斑水肿首选抗VEGF治疗。",
                        "reference": "中华医学会眼科学分会糖尿病性视网膜病变指南 2023"
                    },
                    {
                        "option": "口服糖皮质激素",
                        "is_recommended": False,
                        "reason": "系统激素治疗不推荐用于本病。"
                    },
                    {
                        "option": "激光光凝治疗",
                        "is_recommended": False,
                        "reason": "单独激光效果有限，适用于抗VEGF后残余水肿者。"
                    },
                    {
                        "option": "观察随访",
                        "is_recommended": False,
                        "reason": "有明显视力下降，应积极治疗。"
                    }
                ],
                "recommended_readings": [
                    "《眼科学》第5版，第23章 糖尿病性视网膜病变",
                    "中华医学会眼科学分会糖尿病性黄斑水肿诊疗指南（2023）"
                ]
            },
            {
                "id": 2,
                "title": "急性闭角型青光眼",
                "chief_complaint": "突发眼痛伴视物模糊1天",
                "present_history": "女性，62岁，昨日夜间突然眼痛、头痛、恶心伴视物模糊，今日症状加重。",
                "past_history": "无青光眼史，无糖尿病史。",
                "examinations": [
                    {
                        "name": "视力检查",
                        "result": "右眼光感，左眼0.8。",
                        "weight": 0.1
                    },
                    {
                        "name": "眼压测量",
                        "result": "右眼45 mmHg，左眼15 mmHg。",
                        "weight": 0.3
                    },
                    {
                        "name": "裂隙灯检查",
                        "result": "右眼角膜水肿，前房浅，瞳孔散大固定。",
                        "weight": 0.4
                    },
                    {
                        "name": "OCT",
                        "result": "前房浅，房角关闭。",
                        "weight": 0.2
                    }
                ],
                "differential_diagnoses": [
                    {
                        "option": "急性闭角型青光眼",
                        "is_correct": True,
                        "explanation": "典型急性发作表现，眼压升高，前房浅。"
                    },
                    {
                        "option": "角膜炎",
                        "is_correct": False,
                        "explanation": "虽有眼痛，但无明显角膜浸润或分泌物。"
                    },
                    {
                        "option": "葡萄膜炎",
                        "is_correct": False,
                        "explanation": "前房积脓及虹膜充血缺乏。"
                    }
                ],
                "treatments": [
                    {
                        "option": "立即使用缩瞳药物（如匹罗卡品）",
                        "is_recommended": True,
                        "reason": "有助于开放房角，降低眼压。"
                    },
                    {
                        "option": "静脉甘露醇脱水治疗",
                        "is_recommended": True,
                        "reason": "快速降低眼压，防止视神经损伤。"
                    },
                    {
                        "option": "延迟处理观察",
                        "is_recommended": False,
                        "reason": "此病急需处理，延误可致盲。"
                    }
                ],
                "recommended_readings": [
                    "《眼科学》第5版，第18章 青光眼",
                    "中华医学会青光眼学组诊疗指南（2022）"
                ]
            }
        ]

        # 创建临床案例
        self.create_clinical_cases(clinical_cases_data)
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n=== 临床推理示例数据初始化完成！===\n'
                f'已创建 {len(clinical_cases_data)} 个临床案例\n'
                '可以通过以下方式访问：\n'
                '学生端：http://127.0.0.1:8000/student/clinical-cases/\n'
                '管理后台：http://127.0.0.1:8000/admin/\n'
            )
        )

    def create_clinical_cases(self, cases_data):
        """创建临床案例及相关数据"""
        
        # 获取或创建一个教师用户作为案例创建者
        teacher_user = User.objects.filter(username='teacher1').first()
        if not teacher_user:
            teacher_user = User.objects.create_user(
                username='teacher1',
                email='teacher@example.com',
                password='teacher123',
                first_name='张',
                last_name='教授'
            )
            self.stdout.write('创建教师用户: teacher1')

        for case_data in cases_data:
            case_id = f"CASE_{case_data['id']:03d}"
            
            # 检查案例是否已存在
            if ClinicalCase.objects.filter(case_id=case_id).exists():
                self.stdout.write(f'- 案例已存在：{case_data["title"]} ({case_id})')
                continue

            # 创建临床案例
            clinical_case = ClinicalCase.objects.create(
                case_id=case_id,
                title=case_data['title'],
                patient_age=58 if case_data['id'] == 1 else 62,  # 从病史中提取
                patient_gender='M' if case_data['id'] == 1 else 'F',  # 从病史中提取
                chief_complaint=case_data['chief_complaint'],
                present_illness=case_data['present_history'],
                past_history=case_data['past_history'],
                family_history='',
                learning_objectives=[
                    f"掌握{case_data['title']}的典型临床表现",
                    "学会选择合适的辅助检查",
                    "进行准确的鉴别诊断",
                    "制定合理的治疗方案"
                ],
                difficulty_level='intermediate',
                is_active=True,
                created_by=teacher_user
            )

            # 创建检查选项
            for i, exam in enumerate(case_data['examinations']):
                # 确定检查类型
                exam_type = 'basic'
                if 'OCT' in exam['name']:
                    exam_type = 'imaging'
                elif '眼压' in exam['name']:
                    exam_type = 'basic'
                elif '裂隙灯' in exam['name']:
                    exam_type = 'basic'
                elif '眼底' in exam['name']:
                    exam_type = 'special'

                ExaminationOption.objects.create(
                    clinical_case=clinical_case,
                    examination_type=exam_type,
                    examination_name=exam['name'],
                    examination_description=f"{exam['name']}检查",
                    normal_result="正常范围内",
                    abnormal_result="异常改变",
                    actual_result=exam['result'],
                    diagnostic_value=3 if exam.get('weight', 0) >= 0.3 else (2 if exam.get('weight', 0) >= 0.1 else 1),
                    cost_effectiveness=2,
                    is_recommended=exam.get('weight', 0) > 0.1,
                    display_order=i
                )

            # 创建诊断选项
            for i, diag in enumerate(case_data['differential_diagnoses']):
                DiagnosisOption.objects.create(
                    clinical_case=clinical_case,
                    diagnosis_name=diag['option'],
                    diagnosis_code='',
                    is_correct_diagnosis=diag['is_correct'],
                    is_differential=True,
                    supporting_evidence=diag['explanation'] if diag['is_correct'] else '',
                    contradicting_evidence=diag['explanation'] if not diag['is_correct'] else '',
                    typical_symptoms=[],
                    typical_signs=[],
                    correct_feedback=f"正确！{diag['explanation']}" if diag['is_correct'] else '',
                    incorrect_feedback=f"不正确。{diag['explanation']}" if not diag['is_correct'] else '',
                    probability_score=0.9 if diag['is_correct'] else 0.1,
                    display_order=i
                )

            # 创建治疗选项
            for i, treatment in enumerate(case_data['treatments']):
                TreatmentOption.objects.create(
                    clinical_case=clinical_case,
                    treatment_type='medication' if '药物' in treatment['option'] else 'surgery' if '手术' in treatment['option'] else 'observation' if '观察' in treatment['option'] else 'medication',
                    treatment_name=treatment['option'],
                    treatment_description=treatment['reason'],
                    is_optimal=treatment['is_recommended'],
                    is_acceptable=treatment['is_recommended'],
                    is_contraindicated=not treatment['is_recommended'] and '不推荐' in treatment.get('reason', ''),
                    efficacy_score=3 if treatment['is_recommended'] else 1,
                    safety_score=3 if treatment['is_recommended'] else 2,
                    cost_score=2,
                    expected_outcome=treatment['reason'],
                    potential_complications='',
                    selection_feedback=treatment['reason'],
                    display_order=i
                )

            self.stdout.write(f'✓ 创建临床案例：{clinical_case.title} ({case_id})')
            self.stdout.write(f'  - {len(case_data["examinations"])} 个检查选项')
            self.stdout.write(f'  - {len(case_data["differential_diagnoses"])} 个诊断选项')
            self.stdout.write(f'  - {len(case_data["treatments"])} 个治疗选项')

        self.stdout.write(f'临床案例数据创建完成！总计 {len(cases_data)} 个案例')