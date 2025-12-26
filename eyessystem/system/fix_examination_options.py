#!/usr/bin/env python
"""修正检查选项：删除错误添加的，完善正确检查的结果"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, ExaminationOption

# 获取病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')
print(f"病例: {case.case_id} - {case.title}\n")

# 1. 删除错误添加的检查（B超、角膜内皮细胞计数）
to_delete = ['B超检查', '角膜内皮细胞计数']
for exam_name in to_delete:
    deleted = ExaminationOption.objects.filter(
        clinical_case=case,
        examination_name=exam_name
    ).delete()
    if deleted[0] > 0:
        print(f"✓ 已删除: {exam_name}")

# 2. 更新正确检查的详细结果
updates = {
    '眼科检查': {
        'examination_description': '基础眼科检查，包括外眼检查和视力测定',
        'actual_result': '双眼外观无异常，眼球运动正常。视力：右眼0.3，左眼0.5',
        'diagnostic_value': 3
    },
    '眼底检查': {
        'examination_description': '散瞳后检查眼底情况',
        'actual_result': '双眼眼底隐约可见，因晶状体浑浊影响观察。可见视网膜血管走行正常，视盘边界清晰，黄斑区未见明显异常',
        'diagnostic_value': 2
    },
    '裂隙灯显微镜检查': {
        'examination_description': '观察晶状体混浊部位、类型及程度',
        'actual_result': '双眼晶状体皮质和核均呈灰白色浑浊，右眼浑浊更明显，呈典型的老年性白内障表现。瞳孔区可见明显的灰白色反光。左眼晶状体浑浊相对较轻',
        'diagnostic_value': 3
    }
}

print()
for exam_name, data in updates.items():
    exam = ExaminationOption.objects.filter(
        clinical_case=case,
        examination_name=exam_name
    ).first()
    
    if exam:
        exam.examination_description = data['examination_description']
        exam.actual_result = data['actual_result']
        exam.diagnostic_value = data['diagnostic_value']
        exam.save()
        print(f"✓ 已更新: {exam_name}")
        print(f"  结果: {data['actual_result'][:80]}...")
    else:
        print(f"✗ 未找到: {exam_name}")

print("\n✅ 检查选项修正完成")
print("正确检查（3项）: 眼科检查、眼底检查、裂隙灯显微镜检查")
print("干扰项（1项）: OCT扫描")
