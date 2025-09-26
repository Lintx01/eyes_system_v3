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
        
        # 扩展为20个病例，覆盖常见眼科疾病
        sample_cases = [
            # 1
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
                    }
                ]
            },
            # 2
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
            # 3
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
            },
            # 4
            {
                'title': '视网膜脱离',
                'description': '患者，男性，48岁，突然出现视野缺损，伴飞蚊症和闪光感。',
                'symptoms': '视野缺损、飞蚊症、闪光感',
                'diagnosis': '眼底检查：视网膜裂孔及脱离，玻璃体混浊',
                'difficulty': 'hard',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '视网膜脱离的最常见病因是？',
                        'options': ['外伤', '高度近视', '糖尿病', '青光眼'],
                        'correct_answer': 'B',
                        'explanation': '高度近视导致视网膜变薄，易发生裂孔和脱离。'
                    }
                ]
            },
            # 5
            {
                'title': '黄斑变性',
                'description': '患者，女性，72岁，主诉中心视力下降，视物变形。',
                'symptoms': '中心视力下降、视物变形',
                'diagnosis': 'OCT：黄斑区渗出，视网膜色素上皮脱离',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '老年性黄斑变性的主要危险因素是？',
                        'options': ['高血压', '年龄', '吸烟', '糖尿病'],
                        'correct_answer': 'B',
                        'explanation': '年龄是老年性黄斑变性最重要的危险因素。'
                    }
                ]
            },
            # 6
            {
                'title': '角膜炎',
                'description': '患者，男性，30岁，眼红、疼痛、畏光，伴流泪。',
                'symptoms': '眼红、疼痛、畏光、流泪',
                'diagnosis': '裂隙灯检查：角膜中央溃疡，周围充血',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '细菌性角膜炎最常见的致病菌是？',
                        'options': ['葡萄球菌', '链球菌', '大肠杆菌', '肺炎球菌'],
                        'correct_answer': 'A',
                        'explanation': '葡萄球菌是细菌性角膜炎最常见的致病菌。'
                    }
                ]
            },
            # 7
            {
                'title': '葡萄膜炎',
                'description': '患者，女性，40岁，眼痛、畏光、视力下降，伴虹膜充血。',
                'symptoms': '眼痛、畏光、视力下降、虹膜充血',
                'diagnosis': '前房积脓，虹膜结节，玻璃体混浊',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '葡萄膜炎最常见的并发症是？',
                        'options': ['青光眼', '白内障', '视网膜脱离', '角膜炎'],
                        'correct_answer': 'B',
                        'explanation': '葡萄膜炎可导致继发性白内障。'
                    }
                ]
            },
            # 8
            {
                'title': '视神经炎',
                'description': '患者，女性，28岁，急性视力下降，伴眼球运动痛。',
                'symptoms': '视力下降、眼球运动痛',
                'diagnosis': '视神经乳头水肿，视野中央暗点',
                'difficulty': 'hard',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '视神经炎最常见的病因是？',
                        'options': ['病毒感染', '自身免疫', '外伤', '高血压'],
                        'correct_answer': 'B',
                        'explanation': '自身免疫（如多发性硬化）是视神经炎最常见的病因。'
                    }
                ]
            },
            # 9
            {
                'title': '干眼症',
                'description': '患者，女性，50岁，眼干、异物感、烧灼感，长期使用电脑。',
                'symptoms': '眼干、异物感、烧灼感',
                'diagnosis': '泪液分泌减少，角膜荧光素染色阳性',
                'difficulty': 'easy',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '干眼症最常见的治疗方法是？',
                        'options': ['人工泪液', '抗生素', '激光', '手术'],
                        'correct_answer': 'A',
                        'explanation': '人工泪液是干眼症最常用的治疗方法。'
                    }
                ]
            },
            # 10
            {
                'title': '睑板腺功能障碍',
                'description': '患者，男性，35岁，眼干、睑缘红肿、分泌物增多。',
                'symptoms': '眼干、睑缘红肿、分泌物增多',
                'diagnosis': '睑板腺堵塞，睑缘炎症',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '睑板腺功能障碍最常见的表现是？',
                        'options': ['睑缘红肿', '视力下降', '飞蚊症', '虹膜充血'],
                        'correct_answer': 'A',
                        'explanation': '睑缘红肿和分泌物增多是睑板腺功能障碍的典型表现。'
                    }
                ]
            },
            # 11
            {
                'title': '视网膜中央静脉阻塞',
                'description': '患者，男性，60岁，突然视力下降，伴眼底出血。',
                'symptoms': '视力下降、眼底出血',
                'diagnosis': '眼底检查：火焰状出血，静脉扩张',
                'difficulty': 'hard',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '视网膜中央静脉阻塞最常见的危险因素是？',
                        'options': ['高血压', '糖尿病', '高血脂', '青光眼'],
                        'correct_answer': 'A',
                        'explanation': '高血压是视网膜中央静脉阻塞最重要的危险因素。'
                    }
                ]
            },
            # 12
            {
                'title': '视网膜中央动脉阻塞',
                'description': '患者，男性，58岁，突然无痛性视力丧失。',
                'symptoms': '无痛性视力丧失',
                'diagnosis': '眼底检查：樱桃红斑，视网膜苍白',
                'difficulty': 'hard',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '视网膜中央动脉阻塞的典型眼底表现是？',
                        'options': ['火焰状出血', '樱桃红斑', '玻璃体混浊', '黄斑渗出'],
                        'correct_answer': 'B',
                        'explanation': '樱桃红斑是视网膜中央动脉阻塞的特征性表现。'
                    }
                ]
            },
            # 13
            {
                'title': '虹膜炎',
                'description': '患者，女性，32岁，眼痛、畏光、流泪，虹膜充血。',
                'symptoms': '眼痛、畏光、流泪、虹膜充血',
                'diagnosis': '虹膜充血，前房积脓',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '虹膜炎最常见的症状是？',
                        'options': ['畏光', '视力下降', '飞蚊症', '眼干'],
                        'correct_answer': 'A',
                        'explanation': '畏光和眼痛是虹膜炎最常见的症状。'
                    }
                ]
            },
            # 14
            {
                'title': '眼睑肿瘤',
                'description': '患者，男性，65岁，眼睑出现无痛性肿块，逐渐增大。',
                'symptoms': '眼睑肿块、无痛',
                'diagnosis': '肿块质硬，边界不清，表面溃疡',
                'difficulty': 'hard',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '眼睑恶性肿瘤最常见类型是？',
                        'options': ['基底细胞癌', '鳞状细胞癌', '脂肪瘤', '黑色素瘤'],
                        'correct_answer': 'A',
                        'explanation': '基底细胞癌是眼睑最常见的恶性肿瘤。'
                    }
                ]
            },
            # 15
            {
                'title': '泪囊炎',
                'description': '患者，女性，45岁，流泪、泪囊区肿胀、压痛。',
                'symptoms': '流泪、泪囊区肿胀、压痛',
                'diagnosis': '泪囊区红肿，按压有脓液溢出',
                'difficulty': 'easy',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '慢性泪囊炎最常见的病原菌是？',
                        'options': ['葡萄球菌', '链球菌', '大肠杆菌', '肺炎球菌'],
                        'correct_answer': 'A',
                        'explanation': '葡萄球菌是慢性泪囊炎最常见的病原菌。'
                    }
                ]
            },
            # 16
            {
                'title': '眼外伤',
                'description': '患者，男性，25岁，工作时被异物击中眼部，出现疼痛和流泪。',
                'symptoms': '眼部疼痛、流泪、视力下降',
                'diagnosis': '角膜擦伤，前房积血',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '眼外伤后最需警惕的并发症是？',
                        'options': ['感染', '青光眼', '白内障', '视网膜脱离'],
                        'correct_answer': 'A',
                        'explanation': '感染是眼外伤后最需警惕的并发症。'
                    }
                ]
            },
            # 17
            {
                'title': '弱视',
                'description': '患者，儿童，7岁，视力低于同龄人，矫正镜片后改善有限。',
                'symptoms': '视力低下、单眼优势',
                'diagnosis': '视力检查：单眼视力低于0.5，排除器质性病变',
                'difficulty': 'easy',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '弱视最有效的治疗方法是？',
                        'options': ['遮盖疗法', '药物治疗', '手术', '激光'],
                        'correct_answer': 'A',
                        'explanation': '遮盖疗法是弱视最有效的治疗方法。'
                    }
                ]
            },
            # 18
            {
                'title': '斜视',
                'description': '患者，儿童，5岁，家长发现双眼不能同时注视同一目标。',
                'symptoms': '双眼注视障碍、复视',
                'diagnosis': '眼位检查：内斜视，角度15度',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '斜视最常见的类型是？',
                        'options': ['内斜视', '外斜视', '上斜视', '下斜视'],
                        'correct_answer': 'A',
                        'explanation': '内斜视是儿童斜视最常见的类型。'
                    }
                ]
            },
            # 19
            {
                'title': '色盲',
                'description': '患者，男性，18岁，无法分辨红绿色，家族有类似病史。',
                'symptoms': '红绿色分辨障碍',
                'diagnosis': '色觉检查：红绿色识别障碍',
                'difficulty': 'easy',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '色盲最常见的遗传方式是？',
                        'options': ['常染色体显性', '常染色体隐性', 'X连锁隐性', 'Y连锁'],
                        'correct_answer': 'C',
                        'explanation': '色盲多为X连锁隐性遗传。'
                    }
                ]
            },
            # 20
            {
                'title': '眼部带状疱疹',
                'description': '患者，女性，60岁，眼部皮肤出现水疱，伴眼痛和视力下降。',
                'symptoms': '眼部水疱、眼痛、视力下降',
                'diagnosis': '皮肤水疱沿三叉神经分布，角膜炎症',
                'difficulty': 'medium',
                'case_type': 'clinical',
                'exercises': [
                    {
                        'question': '眼部带状疱疹最常见的并发症是？',
                        'options': ['角膜炎', '虹膜炎', '葡萄膜炎', '视网膜脱离'],
                        'correct_answer': 'A',
                        'explanation': '角膜炎是眼部带状疱疹最常见的并发症。'
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