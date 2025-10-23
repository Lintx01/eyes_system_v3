#!/usr/bin/env python
"""
简单的OCT数据创建脚本 - 直接在当前Django环境中运行
"""

from cases.models import ClinicalCase, ExaminationOption
from django.contrib.auth.models import User

def create_oct_data():
    """创建OCT检查数据"""
    
    # 获取现有的临床案例
    cases = ClinicalCase.objects.all()
    
    if not cases.exists():
        print("没有找到临床案例，请先创建案例")
        return
    
    # 为第一个案例添加OCT检查
    case = cases.first()
    
    # 检查是否已经存在OCT检查
    existing_oct = ExaminationOption.objects.filter(
        clinical_case=case,
        examination_name__icontains='OCT'
    ).exists()
    
    if existing_oct:
        print(f"案例 {case.title} 已存在OCT检查")
        return
    
    # 创建OCT检查选项
    oct_exam = ExaminationOption.objects.create(
        clinical_case=case,
        examination_type='imaging',
        examination_name='OCT光学相干断层扫描',
        examination_description='OCT是一种非侵入性的影像检查技术，能够提供视网膜的高分辨率横截面图像，对于诊断黄斑疾病、青光眼等眼底疾病具有重要价值。',
        normal_result='视网膜各层结构清晰，厚度正常，无积液、出血等病理改变',
        abnormal_result='可见视网膜厚度异常、层间积液、视网膜色素上皮脱离等改变',
        actual_result='''OCT检查显示：
1. 黄斑区视网膜厚度增加，中心凹厚度约420μm（正常<250μm）
2. 视网膜内可见多发微囊样水肿
3. 视网膜色素上皮层连续性良好
4. 未见明显的视网膜色素上皮脱离
5. 玻璃体视网膜界面清晰，无牵拉''',
        diagnostic_value=3,
        cost_effectiveness=2,
        is_oct_exam=True,
        is_recommended=True,
        display_order=10,
        oct_measurement_data={
            "central_thickness": "420μm",
            "average_thickness": "385μm",
            "volume": "12.5mm³",
            "rnfl_superior": "95μm",
            "rnfl_inferior": "88μm",
            "rnfl_nasal": "78μm",
            "rnfl_temporal": "68μm"
        },
        oct_report_text='''OCT检查报告：

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
        image_display_mode='comparison',
        image_findings='黄斑区视网膜厚度增加，可见微囊样水肿，外核层边界模糊'
    )
    
    print(f"成功为案例 '{case.title}' 添加OCT检查")
    print(f"OCT检查ID: {oct_exam.id}")
    print("OCT功能已经准备就绪！")

if __name__ == '__main__':
    create_oct_data()