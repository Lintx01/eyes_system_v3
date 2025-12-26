#!/usr/bin/env python
"""为老年性白内障病例添加完整的检查选项（正确检查+从其他病例抽取干扰项）"""
import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption

# 获取病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.case_id} - {case.title}")

# 删除旧的检查选项（只删除本病例的选项，标记为正确检查的）
# 保留已有的检查选项作为基础
old_count = ExaminationOption.objects.filter(clinical_case=case).count()
print(f"当前有 {old_count} 个检查选项")

# 添加正确的检查选项（诊断白内障需要的）- 只添加不存在的
correct_exams = [
    {
        'examination_type': 'basic',
        'examination_name': '裂隙灯显微镜检查',
        'examination_description': '观察晶状体浑浊情况',
        'actual_result': '双眼晶状体皮质和核均呈灰白色浑浊，右眼浑浊更明显，瞳孔区可见明显的灰白色反光，左眼晶状体浑浊相对较轻',
        'diagnostic_value': 3,  # 高
        'is_required': True,
        'is_correct': True
    },
    {
        'examination_type': 'imaging',
        'examination_name': 'B超检查',
        'examination_description': '检查眼内结构',
        'actual_result': '双眼玻璃体透明，未见明显混浊。视网膜在位，未见脱离。双眼眼轴长度正常',
        'diagnostic_value': 2,  # 中
        'is_required': False,
        'is_correct': True
    },
    {
        'examination_type': 'special',
        'examination_name': '角膜内皮细胞计数',
        'examination_description': '术前评估角膜内皮功能',
        'actual_result': '右眼角膜内皮细胞密度：2450个/mm²，左眼：2580个/mm²（正常范围）',
        'diagnostic_value': 2,  # 中
        'is_required': False,
        'is_correct': True
    },
]

# 创建正确的检查选项
created_correct = 0
for exam_data in correct_exams:
    # 检查是否已存在
    exists = ExaminationOption.objects.filter(
        clinical_case=case,
        examination_name=exam_data['examination_name']
    ).exists()
    
    if not exists:
        ExaminationOption.objects.create(
            clinical_case=case,
            examination_type=exam_data['examination_type'],
            examination_name=exam_data['examination_name'],
            examination_description=exam_data['examination_description'],
            normal_result='正常',
            actual_result=exam_data['actual_result'],
            diagnostic_value=exam_data['diagnostic_value'],
            cost_effectiveness=2,
            is_required=exam_data['is_required']
        )
        created_correct += 1
        print(f"✓ 添加正确检查: {exam_data['examination_name']}")
    else:
        print(f"- 已存在: {exam_data['examination_name']}")

# 从其他病例获取干扰项（随机抽取3-5个其他病例的检查选项）
other_cases = ClinicalCase.objects.exclude(case_id=case.case_id)
if other_cases.exists():
    # 获取其他病例的所有检查选项
    other_exam_options = ExaminationOption.objects.filter(
        clinical_case__in=other_cases
    ).exclude(
        examination_name__in=[e['examination_name'] for e in correct_exams]
    )
    
    # 随机选择3-5个作为干扰项
    distractor_count = min(5, other_exam_options.count())
    if distractor_count > 0:
        distractors = random.sample(list(other_exam_options), distractor_count)
        
        created_distractors = 0
        for distractor in distractors:
            # 检查是否已存在
            exists = ExaminationOption.objects.filter(
                clinical_case=case,
                examination_name=distractor.examination_name
            ).exists()
            
            if not exists:
                # 创建干扰项（复制检查选项但结果为"无相关检查信息"）
                ExaminationOption.objects.create(
                    clinical_case=case,
                    examination_type=distractor.examination_type,
                    examination_name=distractor.examination_name,
                    examination_description=distractor.examination_description,
                    normal_result='正常',
                    actual_result='无相关检查信息',  # 干扰项返回空信息
                    diagnostic_value=1,  # 低诊断价值
                    cost_effectiveness=1,
                    is_required=False
                )
                created_distractors += 1
                print(f"✓ 添加干扰项: {distractor.examination_name} (来自其他病例)")
        
        print(f"\n✅ 成功添加检查选项:")
        print(f"   - 正确检查: {created_correct} 项")
        print(f"   - 干扰项: {created_distractors} 项")
    else:
        print("\n⚠️ 其他病例中没有可用的检查选项作为干扰项")
else:
    print("\n⚠️ 数据库中没有其他病例，无法添加干扰项")
