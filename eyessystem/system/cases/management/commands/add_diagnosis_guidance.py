#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为诊断选项添加循序渐进的智能指导内容
"""

from django.core.management.base import BaseCommand
from cases.models import DiagnosisOption, ClinicalCase


class Command(BaseCommand):
    help = '为诊断选项添加循序渐进的智能指导内容'

    def handle(self, *args, **options):
        """添加诊断指导内容"""
        
        # 示例指导内容模板
        guidance_templates = {
            '青光眼': {
                'hint_level_1': '注意患者的眼压值和视野缺损情况',
                'hint_level_2': '高眼压(>21mmHg)、视野缺损和视盘凹陷是青光眼的重要指标',
                'hint_level_3': '该患者眼压明显升高，伴有视野缺损和视盘凹陷增大，符合青光眼的典型表现'
            },
            '白内障': {
                'hint_level_1': '观察晶状体的透明度变化',
                'hint_level_2': '晶状体混浊导致视力下降是白内障的主要特征',
                'hint_level_3': '该患者晶状体明显混浊，视力显著下降，符合白内障诊断'
            },
            '糖尿病视网膜病变': {
                'hint_level_1': '结合患者的糖尿病病史和眼底检查',
                'hint_level_2': '微血管瘤、出血点和渗出物是糖尿病视网膜病变的典型表现',
                'hint_level_3': '该患者有糖尿病史，眼底可见微血管瘤、出血和硬性渗出，诊断为糖尿病视网膜病变'
            },
            '黄斑变性': {
                'hint_level_1': '注意患者的中心视力和黄斑区变化',
                'hint_level_2': '黄斑区色素紊乱、玻璃膜疣和地图样萎缩是黄斑变性的特征',
                'hint_level_3': '该患者中心视力下降，黄斑区可见典型的地图样萎缩改变'
            },
            '视网膜脱离': {
                'hint_level_1': '考虑患者的视野缺损类型和眼底改变',
                'hint_level_2': '幕状视野缺损、视网膜隆起是视网膜脱离的重要征象',
                'hint_level_3': '该患者出现典型的幕状视野缺损，眼底检查可见视网膜脱离'
            },
            '角膜炎': {
                'hint_level_1': '注意患者的眼部疼痛和角膜改变',
                'hint_level_2': '角膜水肿、浑浊伴有疼痛、畏光是角膜炎的典型症状',
                'hint_level_3': '该患者角膜明显水肿浑浊，伴有剧烈疼痛和畏光，符合角膜炎诊断'
            },
            '结膜炎': {
                'hint_level_1': '观察结膜的充血和分泌物情况',
                'hint_level_2': '结膜充血、水肿伴有分泌物增多是结膜炎的主要表现',
                'hint_level_3': '该患者结膜明显充血水肿，有脓性分泌物，诊断为细菌性结膜炎'
            },
            '近视性黄斑病变': {
                'hint_level_1': '结合患者的屈光度和黄斑区改变',
                'hint_level_2': '高度近视患者容易发生黄斑裂孔、脉络膜新生血管等病变',
                'hint_level_3': '该高度近视患者黄斑区可见裂孔形成，符合近视性黄斑病变'
            }
        }
        
        # 获取所有诊断选项
        diagnosis_options = DiagnosisOption.objects.all()
        updated_count = 0
        
        for option in diagnosis_options:
            diagnosis_name = option.diagnosis_name.strip()
            
            # 查找匹配的指导模板
            matched_template = None
            for template_name, template_content in guidance_templates.items():
                if template_name in diagnosis_name or diagnosis_name in template_name:
                    matched_template = template_content
                    break
            
            if matched_template:
                # 更新指导内容
                option.hint_level_1 = matched_template['hint_level_1']
                option.hint_level_2 = matched_template['hint_level_2']
                option.hint_level_3 = matched_template['hint_level_3']
                option.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 已为 "{diagnosis_name}" 添加指导内容')
                )
            else:
                # 添加通用指导内容
                option.hint_level_1 = f'请仔细分析患者的症状和检查结果，考虑是否符合{diagnosis_name}的典型表现'
                option.hint_level_2 = f'回顾{diagnosis_name}的诊断标准和临床特征，与患者情况对比分析'
                option.hint_level_3 = f'根据临床证据判断：该患者的表现与{diagnosis_name}的符合程度如何？'
                option.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'○ 已为 "{diagnosis_name}" 添加通用指导内容')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ 完成！共为 {updated_count} 个诊断选项添加了智能指导内容。')
        )
        self.stdout.write(
            self.style.SUCCESS('🎯 智能指导功能已准备就绪，学生在诊断错误时将获得循序渐进的指导。')
        )