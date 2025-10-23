from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from cases.models import ClinicalCase, ExaminationOption
import json


class Command(BaseCommand):
    help = '为临床案例添加OCT检查选项'

    def handle(self, *args, **options):
        self.stdout.write('开始添加OCT检查选项...')
        
        try:
            # 获取现有的临床案例
            clinical_cases = ClinicalCase.objects.all()
            
            if not clinical_cases.exists():
                self.stdout.write(
                    self.style.WARNING('没有找到临床案例，请先运行 init_clinical_data 命令')
                )
                return
            
            # 为每个案例添加OCT检查
            for case in clinical_cases:
                self.add_oct_examinations(case)
            
            self.stdout.write(
                self.style.SUCCESS(f'成功为 {clinical_cases.count()} 个案例添加OCT检查选项')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'添加OCT检查选项时发生错误: {str(e)}')
            )

    def add_oct_examinations(self, case):
        """为指定案例添加OCT检查选项"""
        
        # 检查是否已存在OCT检查
        existing_oct = ExaminationOption.objects.filter(
            clinical_case=case,
            is_oct_exam=True
        ).exists()
        
        if existing_oct:
            self.stdout.write(f'案例 {case.title} 已存在OCT检查，跳过')
            return
        
        # 创建OCT检查选项
        oct_exam = ExaminationOption.objects.create(
            clinical_case=case,
            examination_type='imaging',
            examination_name='OCT光学相干断层扫描',
            examination_description='用于观察视网膜各层结构，检测视网膜厚度变化、积液、出血等病理改变。是诊断黄斑疾病、青光眼等眼底疾病的重要检查手段。',
            normal_result='视网膜各层结构清晰，厚度正常，无积液、出血等病理改变',
            abnormal_result='可见视网膜厚度异常、层间积液、视网膜色素上皮脱离等改变',
            actual_result=self.get_oct_result_by_case(case),
            diagnostic_value=3,  # 高诊断价值
            cost_effectiveness=2,  # 中等成本效益
            is_oct_exam=True,
            is_recommended=True,
            display_order=10,
            # OCT测量数据示例
            oct_measurement_data=self.get_oct_measurements_by_case(case),
            oct_report_text=self.get_oct_report_by_case(case),
            image_display_mode='comparison',
            image_findings=self.get_oct_findings_by_case(case)
        )
        
        self.stdout.write(f'为案例 {case.title} 添加OCT检查: {oct_exam.examination_name}')

    def get_oct_result_by_case(self, case):
        """根据案例类型返回相应的OCT检查结果"""
        case_title_lower = case.title.lower()
        
        if '糖尿病' in case.title or '糖网' in case.title:
            return """OCT检查显示：
1. 黄斑区视网膜厚度增加，中心凹厚度约420μm（正常<250μm）
2. 视网膜内可见多发微囊样水肿
3. 视网膜色素上皮层连续性良好
4. 未见明显的视网膜色素上皮脱离
5. 玻璃体视网膜界面清晰，无牵拉"""

        elif '高血压' in case.title:
            return """OCT检查显示：
1. 视网膜神经纤维层厚度轻度减薄
2. 黄斑区视网膜厚度基本正常
3. 可见少量视网膜内出血点
4. 视网膜色素上皮层稍有不规整
5. 无明显黄斑水肿"""

        elif '静脉阻塞' in case.title or '阻塞' in case.title:
            return """OCT检查显示：
1. 黄斑区显著水肿，中心凹厚度达650μm
2. 视网膜内大量囊样水肿空间
3. 视网膜各层结构模糊不清
4. 视网膜下少量积液
5. 视网膜色素上皮层部分脱离"""

        else:
            return """OCT检查显示：
1. 黄斑区视网膜厚度正常
2. 视网膜各层结构清晰
3. 视网膜色素上皮层连续完整
4. 无明显病理性改变
5. 视网膜下间隙清晰"""

    def get_oct_measurements_by_case(self, case):
        """根据案例返回OCT测量数据"""
        case_title_lower = case.title.lower()
        
        if '糖尿病' in case.title:
            return {
                "central_thickness": "420μm",
                "average_thickness": "385μm", 
                "volume": "12.5mm³",
                "rnfl_superior": "95μm",
                "rnfl_inferior": "88μm",
                "rnfl_nasal": "78μm",
                "rnfl_temporal": "68μm"
            }
        elif '高血压' in case.title:
            return {
                "central_thickness": "245μm",
                "average_thickness": "278μm",
                "volume": "8.9mm³", 
                "rnfl_superior": "92μm",
                "rnfl_inferior": "95μm",
                "rnfl_nasal": "75μm",
                "rnfl_temporal": "71μm"
            }
        elif '静脉阻塞' in case.title:
            return {
                "central_thickness": "650μm",
                "average_thickness": "520μm",
                "volume": "16.8mm³",
                "rnfl_superior": "110μm", 
                "rnfl_inferior": "125μm",
                "rnfl_nasal": "95μm",
                "rnfl_temporal": "85μm"
            }
        else:
            return {
                "central_thickness": "238μm",
                "average_thickness": "275μm",
                "volume": "8.7mm³",
                "rnfl_superior": "100μm",
                "rnfl_inferior": "105μm", 
                "rnfl_nasal": "80μm",
                "rnfl_temporal": "75μm"
            }

    def get_oct_report_by_case(self, case):
        """根据案例返回OCT报告文字"""
        case_title_lower = case.title.lower()
        
        if '糖尿病' in case.title:
            return """OCT检查报告：

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
3. 定期OCT随访观察"""

        elif '静脉阻塞' in case.title:
            return """OCT检查报告：

检查部位：右眼黄斑区  
检查日期：2024年10月22日

检查所见：
1. 黄斑区视网膜显著水肿，中心凹厚度650μm
2. 视网膜内见大量囊样水肿空间，呈"蜂窝状"改变
3. 视网膜外层结构破坏，IS/OS连接线中断
4. 视网膜下见少量积液
5. 视网膜色素上皮部分不规整脱离

诊断意见：
符合视网膜静脉阻塞继发黄斑囊样水肿的OCT表现。

建议：
1. 玻璃体腔注射抗VEGF药物
2. 密切随访，每月复查OCT
3. 必要时考虑激光光凝治疗"""

        else:
            return """OCT检查报告：

检查部位：双眼黄斑区
检查日期：2024年10月22日

检查所见：
1. 黄斑区视网膜厚度正常，中心凹厚度238μm
2. 视网膜各层结构清晰可辨，层次分明
3. 视网膜神经纤维层厚度正常
4. 视网膜色素上皮层连续完整
5. 脉络膜厚度正常

诊断意见：
OCT检查未见明显异常，视网膜结构正常。

建议：
定期健康体检，如有视力变化及时就诊。"""

    def get_oct_findings_by_case(self, case):
        """根据案例返回OCT图像所见"""
        case_title_lower = case.title.lower()
        
        if '糖尿病' in case.title:
            return "黄斑区视网膜厚度增加，可见微囊样水肿，外核层边界模糊"
        elif '高血压' in case.title:
            return "视网膜神经纤维层轻度变薄，可见少量出血点"
        elif '静脉阻塞' in case.title:
            return "黄斑区显著囊样水肿，视网膜下积液，RPE部分脱离"
        else:
            return "视网膜各层结构正常，厚度在正常范围内"