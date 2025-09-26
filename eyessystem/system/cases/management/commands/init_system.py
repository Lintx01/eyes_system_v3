"""
Django管理命令：初始化眼科教学系统
使用方法：python manage.py init_system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from cases.permissions import setup_groups_and_permissions, create_test_users
from cases.models import Case, Exercise
import json


class Command(BaseCommand):
    help = '初始化眼科教学系统的用户组、权限和示例数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='跳过创建测试用户',
        )
        parser.add_argument(
            '--skip-data',
            action='store_true',
            help='跳过创建示例数据',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化眼科教学系统...'))

        # 1. 设置用户组和权限
        self.stdout.write('1. 设置用户组和权限...')
        setup_groups_and_permissions()
        self.stdout.write(self.style.SUCCESS('✓ 用户组和权限设置完成'))

        # 2. 创建测试用户
        if not options['skip_users']:
            self.stdout.write('2. 创建测试用户...')
            create_test_users()
            self.stdout.write(self.style.SUCCESS('✓ 测试用户创建完成'))

        # 3. 创建示例数据
        if not options['skip_data']:
            self.stdout.write('3. 创建示例数据...')
            self.create_sample_data()
            self.stdout.write(self.style.SUCCESS('✓ 示例数据创建完成'))

        self.stdout.write(
            self.style.SUCCESS(
                '\n=== 初始化完成！===\n'
                '测试账户信息：\n'
                '教师账户：teacher1 / teacher123\n'
                '学生账户：student1, student2, student3 / student123\n'
                '\n'
                '管理后台：http://127.0.0.1:8000/admin/\n'
                '学生界面：http://127.0.0.1:8000/\n'
                '教师界面：http://127.0.0.1:8000/teacher/\n'
            )
        )

    def create_sample_data(self):
        """创建示例病例和练习题目"""
        
        # 示例病例数据
        sample_cases = [
            {
                'title': '青光眼典型病例',
                'description': '患者，男性，65岁，主诉双眼视力下降1年，视野缺损。患者有高眼压家族史。',
                'symptoms': '双眼视力下降、眼胀痛、视野缺损、夜间视力差、头痛',
                'diagnosis': '眼压：右眼25mmHg，左眼28mmHg；视野检查：双眼视野缺损；OCT：视神经纤维层变薄；房角镜检查：房角开放',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '根据以上病例，该患者最可能的诊断是？',
                        'options': ['白内障', '青光眼', '视网膜脱离', '糖尿病视网膜病变'],
                        'correct_answer': 'B',
                        'explanation': '患者眼压升高（>21mmHg），视野缺损，视神经纤维层变薄，符合青光眼的典型表现。青光眼是由于眼内压升高导致的视神经病变。'
                    },
                    {
                        'question': '青光眼的主要致病因素是什么？',
                        'options': ['眼压升高', '血糖升高', '血压升高', '胆固醇升高'],
                        'correct_answer': 'A',
                        'explanation': '眼压升高是青光眼最主要的致病因素，正常眼压为10-21mmHg，超过此范围可能损害视神经。'
                    }
                ]
            },
            {
                'title': '糖尿病视网膜病变',
                'description': '患者，男性，55岁，糖尿病史15年，主诉右眼视力下降，伴视物变形。',
                'symptoms': '右眼视力下降、视物变形、中心暗点、夜间视力下降',
                'diagnosis': '眼底检查：视网膜出血、渗出、微动脉瘤；OCT：黄斑区水肿；FFA：毛细血管无灌注区；糖化血红蛋白9.2%',
                'difficulty': 'hard',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '糖尿病视网膜病变的分期，本患者属于？',
                        'options': ['轻度非增殖期', '中度非增殖期', '重度非增殖期', '增殖期'],
                        'correct_answer': 'B',
                        'explanation': '患者有微动脉瘤、出血和渗出，但无新生血管，属于中度非增殖性糖尿病视网膜病变。'
                    }
                ]
            },
            {
                'title': '白内障病例',
                'description': '患者，女性，70岁，主诉双眼视力模糊，渐进性加重2年。',
                'symptoms': '双眼视力模糊、畏光、眩光、夜间视力下降、色彩辨别能力下降',
                'diagnosis': '视力：右眼0.3，左眼0.4；裂隙灯检查：双眼晶状体皮质及核混浊；眼底检查：视网膜模糊不清',
                'difficulty': 'easy',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '白内障的主要治疗方法是？',
                        'options': ['药物治疗', '激光治疗', '手术治疗', '物理治疗'],
                        'correct_answer': 'C',
                        'explanation': '白内障的根本治疗方法是手术摘除混浊的晶状体并植入人工晶状体。药物治疗只能延缓发展，无法逆转。'
                    }
                ]
            }
        ]

        # 创建病例和练习
        for case_data in sample_cases:
            # 检查是否已存在
            if not Case.objects.filter(title=case_data['title']).exists():
                case = Case.objects.create(
                    title=case_data['title'],
                    description=case_data['description'],
                    symptoms=case_data['symptoms'],
                    diagnosis=case_data['diagnosis'],
                    difficulty=case_data['difficulty'],
                    case_type=case_data['case_type'],
                    is_active=True
                )
                
                # 创建相关练习题目
                for ex_data in case_data['exercises']:
                    Exercise.objects.create(
                        case=case,
                        question=ex_data['question'],
                        question_type='single',
                        options=json.dumps(ex_data['options'], ensure_ascii=False),
                        correct_answer=ex_data['correct_answer'],
                        explanation=ex_data['explanation'],
                        difficulty=2,
                        is_active=True
                    )
                
                self.stdout.write(f'✓ 创建病例：{case.title} ({len(case_data["exercises"])}道练习题)')
            else:
                self.stdout.write(f'- 病例已存在：{case_data["title"]}')

        self.stdout.write(f'示例数据创建完成！总计 {len(sample_cases)} 个病例')