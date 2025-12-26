#!/usr/bin/env python
"""
设置病人回答模板的脚本
为交互式问诊功能创建示例数据
"""

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, PatientResponseTemplate

def create_sample_templates():
    """为现有病例创建示例病人回答模板"""
    
    # 获取第一个病例作为示例
    try:
        case = ClinicalCase.objects.first()
        if not case:
            print("没有找到临床病例，请先创建病例数据")
            return
            
        print(f"为病例 '{case.title}' 创建病人回答模板...")
        
        # 创建病人回答模板
        templates = [
            {
                'keywords': ['视力', '看不清', '模糊', '视物不清'],
                'response_text': '我最近几个月感觉看东西越来越模糊，尤其是看远处的东西。开始以为是老花眼，但戴眼镜也没有改善。',
                'information_category': 'chief_complaint',
                'diagnostic_importance': 'critical',
                'priority': 100
            },
            {
                'keywords': ['疼痛', '痛', '疼', '胀痛', '眼痛'],
                'response_text': '偶尔会感到眼部有轻微的胀痛感，特别是在用眼过度的时候，但不是很严重。',
                'information_category': 'present_illness',
                'diagnostic_importance': 'important',
                'priority': 80
            },
            {
                'keywords': ['多久了', '什么时候开始', '持续时间', '病程'],
                'response_text': '大概是3-4个月前开始的，刚开始症状很轻微，以为是疲劳引起的，但最近越来越明显了。',
                'information_category': 'present_illness',
                'diagnostic_importance': 'critical',
                'priority': 95
            },
            {
                'keywords': ['家族史', '家人', '遗传', '父母'],
                'response_text': '我母亲有糖尿病，父亲有高血压。不过他们都没有明显的眼科疾病。',
                'information_category': 'family_history',
                'diagnostic_importance': 'important',
                'priority': 70
            },
            {
                'keywords': ['既往史', '以前', '病史', '其他疾病'],
                'response_text': '我有轻微的高血压，在服用降压药控制。其他没有什么大的疾病。',
                'information_category': 'past_history',
                'diagnostic_importance': 'important',
                'priority': 75
            },
            {
                'keywords': ['症状', '还有什么', '其他表现'],
                'response_text': '除了视力模糊，有时候会感觉眼前有小黑点飘动，特别是看白色背景的时候比较明显。',
                'information_category': 'present_illness',
                'diagnostic_importance': 'important',
                'priority': 85
            },
            {
                'keywords': ['晚上', '夜间', '光线', '暗处'],
                'response_text': '晚上看东西确实更困难一些，路灯下的光晕比以前大了很多。',
                'information_category': 'present_illness',
                'diagnostic_importance': 'important',
                'priority': 80
            },
            {
                'keywords': ['工作', '职业', '用眼'],
                'response_text': '我是会计，平时用电脑比较多，可能用眼过度。最近工作时感觉很吃力。',
                'information_category': 'personal_history',
                'diagnostic_importance': 'supportive',
                'priority': 60
            },
            {
                'keywords': ['检查', '就医', '看过医生'],
                'response_text': '之前去过社区医院，医生说可能是老花眼，但配了眼镜效果不好，所以来这里检查。',
                'information_category': 'present_illness',
                'diagnostic_importance': 'supportive',
                'priority': 65
            },
            {
                'keywords': ['药物', '用药', '治疗'],
                'response_text': '目前只在用降压药（氨氯地平），没有用过其他眼科相关的药物。',
                'information_category': 'past_history',
                'diagnostic_importance': 'supportive',
                'priority': 55
            }
        ]
        
        # 删除该病例现有的模板（如果有的话）
        PatientResponseTemplate.objects.filter(case=case).delete()
        
        # 创建新模板
        created_count = 0
        for template_data in templates:
            template = PatientResponseTemplate.objects.create(
                case=case,
                **template_data
            )
            created_count += 1
            print(f"✓ 创建模板: {template.get_information_category_display()} - {template.response_text[:30]}...")
        
        print(f"\n成功为病例 '{case.title}' 创建了 {created_count} 个病人回答模板！")
        
        # 显示统计信息
        total_templates = PatientResponseTemplate.objects.filter(case=case).count()
        print(f"该病例现有模板总数: {total_templates}")
        
    except Exception as e:
        print(f"创建模板时发生错误: {e}")

if __name__ == "__main__":
    create_sample_templates()