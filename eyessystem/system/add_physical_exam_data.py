#!/usr/bin/env python
"""为病例CCC7D361F8添加体格检查信息"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase

# 获取病例
case = ClinicalCase.objects.get(case_id='CCC7D361F8')

print(f"病例: {case.case_id} - {case.title}")
print(f"患者: {case.patient_age}岁 {case.get_patient_gender_display()}")

# 添加体格检查信息（老年性白内障典型体征）
case.visual_acuity = "右眼：0.3（矫正视力0.4），左眼：0.5（矫正视力0.6）"
case.intraocular_pressure = "右眼：15mmHg，左眼：16mmHg（正常范围）"
case.external_eye_exam = "双眼眼睑正常，眼球位置居中，运动自如，无眼球突出或凹陷"
case.pupil_exam = "双眼瞳孔等大等圆，直径约3mm，对光反射存在但稍迟钝"
case.conjunctiva_exam = "双眼结膜无充血，无分泌物"
case.cornea_exam = "双眼角膜透明，表面光滑，未见明显浑浊"

case.save()

print("\n✅ 体格检查信息已添加：")
print(f"视力: {case.visual_acuity}")
print(f"眼压: {case.intraocular_pressure}")
print(f"眼外观: {case.external_eye_exam}")
print(f"瞳孔: {case.pupil_exam}")
print(f"结膜: {case.conjunctiva_exam}")
print(f"角膜: {case.cornea_exam}")
