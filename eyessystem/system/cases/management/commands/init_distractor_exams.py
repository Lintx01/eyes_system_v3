#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from cases.models import ExaminationOption, ClinicalCase


class Command(BaseCommand):
    help = '初始化通用检查项目池（用作干扰项）'

    def handle(self, *args, **options):
        """
        创建通用检查项目池，这些项目不属于任何特定案例，
        用作学生检查选择时的干扰项
        """
        
        # 创建一个虚拟的通用案例来承载干扰项
        distractor_case, created = ClinicalCase.objects.get_or_create(
            case_id='DISTRACTOR_POOL',
            defaults={
                'title': '通用检查项目池（系统用）',
                'description': '用于生成干扰项的通用检查项目池，不用于教学',
                'difficulty_level': 'intermediate',
                'target_diagnosis': '系统用途',
                'is_active': False,  # 不在正常教学中显示
                'created_by_id': 1  # 假设管理员ID为1
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'创建通用案例: {distractor_case.title}'))
        
        # 定义通用检查项目数据
        distractor_examinations = [
            # 基础检查类
            {
                'examination_name': '血常规检查',
                'examination_type': 'laboratory',
                'examination_description': '检查血液中各种细胞成分和生化指标',
                'diagnostic_value': 'low',
                'cost_effectiveness': 'high',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '尿常规检查',
                'examination_type': 'laboratory',
                'examination_description': '检查尿液成分，了解肾脏和泌尿系统功能',
                'diagnostic_value': 'low',
                'cost_effectiveness': 'high',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '肝功能检查',
                'examination_type': 'laboratory',
                'examination_description': '评估肝脏代谢功能和损伤程度',
                'diagnostic_value': 'low',
                'cost_effectiveness': 'medium',
                'is_recommended': False,
                'is_required': False
            },
            
            # 眼科相关但通用的检查
            {
                'examination_name': '色觉检查',
                'examination_type': 'functional',
                'examination_description': '检查患者对颜色的识别能力',
                'diagnostic_value': 'low',
                'cost_effectiveness': 'high',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '立体视觉检查',
                'examination_type': 'functional',
                'examination_description': '评估双眼立体视觉功能',
                'diagnostic_value': 'low',
                'cost_effectiveness': 'medium',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '调节功能检查',
                'examination_type': 'functional',
                'examination_description': '检查眼睛的调节能力',
                'diagnostic_value': 'medium',
                'cost_effectiveness': 'medium',
                'is_recommended': False,
                'is_required': False
            },
            
            # 影像学检查
            {
                'examination_name': '头部CT检查',
                'examination_type': 'imaging',
                'examination_description': '检查头部结构，排除颅内病变',
                'diagnostic_value': 'medium',
                'cost_effectiveness': 'low',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '眼眶MRI检查',
                'examination_type': 'imaging',
                'examination_description': '详细观察眼眶内软组织结构',
                'diagnostic_value': 'high',
                'cost_effectiveness': 'low',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': 'B超检查（眼部）',
                'examination_type': 'imaging',
                'examination_description': '超声检查眼球内部结构',
                'diagnostic_value': 'medium',
                'cost_effectiveness': 'high',
                'is_recommended': False,
                'is_required': False
            },
            
            # 专科检查
            {
                'examination_name': '眼底血管造影',
                'examination_type': 'imaging',
                'examination_description': '显影检查视网膜血管循环',
                'diagnostic_value': 'high',
                'cost_effectiveness': 'low',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '角膜厚度测量',
                'examination_type': 'functional',
                'examination_description': '测量角膜中央厚度',
                'diagnostic_value': 'medium',
                'cost_effectiveness': 'medium',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '泪液分泌试验',
                'examination_type': 'functional',
                'examination_description': '评估泪腺分泌功能',
                'diagnostic_value': 'medium',
                'cost_effectiveness': 'high',
                'is_recommended': False,
                'is_required': False
            },
            
            # 电生理检查
            {
                'examination_name': '视觉诱发电位',
                'examination_type': 'functional',
                'examination_description': '检查视觉通路的电生理功能',
                'diagnostic_value': 'high',
                'cost_effectiveness': 'medium',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '眼电图检查',
                'examination_type': 'functional',
                'examination_description': '记录眼球运动的电位变化',
                'diagnostic_value': 'medium',
                'cost_effectiveness': 'medium',
                'is_recommended': False,
                'is_required': False
            },
            
            # 其他辅助检查
            {
                'examination_name': '血糖检查',
                'examination_type': 'laboratory',
                'examination_description': '检查血液葡萄糖水平',
                'diagnostic_value': 'low',
                'cost_effectiveness': 'high',
                'is_recommended': False,
                'is_required': False
            },
            {
                'examination_name': '血压测量',
                'examination_type': 'physical',
                'examination_description': '测量体循环动脉血压',
                'diagnostic_value': 'low',
                'cost_effectiveness': 'high',
                'is_recommended': False,
                'is_required': False
            },
        ]
        
        # 批量创建干扰项检查
        created_count = 0
        for exam_data in distractor_examinations:
            examination, created = ExaminationOption.objects.get_or_create(
                clinical_case=distractor_case,
                examination_name=exam_data['examination_name'],
                defaults=exam_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  创建检查项目: {examination.examination_name}')
            else:
                self.stdout.write(f'  检查项目已存在: {examination.examination_name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'干扰项初始化完成！新创建 {created_count} 个检查项目')
        )
        self.stdout.write(
            self.style.WARNING(f'总计干扰项数量: {ExaminationOption.objects.filter(clinical_case=distractor_case).count()}')
        )
        
        # 显示统计信息
        total_distractors = ExaminationOption.objects.filter(clinical_case=distractor_case).count()
        by_type = {}
        for exam in ExaminationOption.objects.filter(clinical_case=distractor_case):
            exam_type = exam.get_examination_type_display()
            by_type[exam_type] = by_type.get(exam_type, 0) + 1
        
        self.stdout.write('\n干扰项分类统计:')
        for exam_type, count in by_type.items():
            self.stdout.write(f'  {exam_type}: {count} 项')