#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化鉴别诊断选项配置 - 参考检查选项的设计逻辑
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import DiagnosisOption, ClinicalCase


def optimize_diagnosis_options():
    """优化诊断选项配置，参考检查选项设计"""
    
    print("=== 优化鉴别诊断选项配置 ===\n")
    
    # 获取案例
    case = ClinicalCase.objects.first()
    if not case:
        print("❌ 没有找到案例")
        return
        
    print(f"📋 案例: {case.case_id} - {case.title}")
    
    # 获取所有诊断选项
    diagnosis_options = DiagnosisOption.objects.filter(clinical_case=case)
    
    print(f"\n🔍 当前诊断选项 ({diagnosis_options.count()}个):")
    for opt in diagnosis_options:
        print(f"  - {opt.diagnosis_name}: 正确={opt.is_correct_diagnosis}, 概率={opt.probability_score}")
    
    # 定义优化配置 - 参考检查选项的设计逻辑
    optimization_configs = {
        # 正确诊断配置
        '糖尿病视网膜病变': {
            'is_correct_diagnosis': True,
            'is_required': True,  # 必选正确诊断
            'is_recommended': True,
            'diagnostic_difficulty': 2,  # 中等难度
            'interference_level': 1,  # 不是干扰项
            'probability_score': 0.95,
            'display_order': 1
        },
        '视网膜动脉阻塞': {
            'is_correct_diagnosis': True,
            'is_required': True,  # 必选正确诊断
            'is_recommended': True,
            'diagnostic_difficulty': 3,  # 困难识别
            'interference_level': 1,
            'probability_score': 0.90,
            'display_order': 2
        },
        
        # 干扰项配置（参考检查选项的推荐但非必需逻辑）
        '视网膜分支静脉阻塞': {
            'is_correct_diagnosis': False,
            'is_required': False,
            'is_recommended': False,  # 不推荐的干扰项
            'diagnostic_difficulty': 2,
            'interference_level': 3,  # 高干扰（相似疾病）
            'probability_score': 0.65,  # 较高概率干扰项
            'display_order': 3
        },
        '青光眼': {
            'is_correct_diagnosis': False,
            'is_required': False,
            'is_recommended': False,
            'diagnostic_difficulty': 1,  # 容易排除
            'interference_level': 2,  # 中等干扰
            'probability_score': 0.15,
            'display_order': 4
        },
        '白内障': {
            'is_correct_diagnosis': False,
            'is_required': False,
            'is_recommended': False,
            'diagnostic_difficulty': 1,  # 容易排除
            'interference_level': 1,  # 低干扰
            'probability_score': 0.05,
            'display_order': 5
        },
        '黄斑变性': {
            'is_correct_diagnosis': False,
            'is_required': False,
            'is_recommended': False,
            'diagnostic_difficulty': 2,
            'interference_level': 2,  # 中等干扰
            'probability_score': 0.25,
            'display_order': 6
        }
    }
    
    # 应用优化配置
    updated_count = 0
    print(f"\n🔧 应用优化配置:")
    
    for diagnosis_name, config in optimization_configs.items():
        try:
            option = diagnosis_options.get(diagnosis_name=diagnosis_name)
            
            # 更新配置
            for field, value in config.items():
                setattr(option, field, value)
            
            option.save()
            updated_count += 1
            
            # 显示配置详情
            status = "✅ 正确" if option.is_correct_diagnosis else "❌ 干扰"
            required = "🔴 必选" if option.is_required else "⚪ 可选"
            difficulty = ["🟢 容易", "🟡 中等", "🔴 困难"][option.diagnostic_difficulty - 1]
            interference = ["🟢 低", "🟡 中", "🔴 高"][option.interference_level - 1]
            
            print(f"  {status} {diagnosis_name}: {required} | 难度:{difficulty} | 干扰:{interference} | 概率:{option.probability_score}")
            
        except DiagnosisOption.DoesNotExist:
            print(f"  ⚠️ 诊断选项不存在: {diagnosis_name}")
    
    # 显示最终统计
    print(f"\n📊 优化后统计:")
    updated_options = DiagnosisOption.objects.filter(clinical_case=case).order_by('display_order')
    
    required_correct = updated_options.filter(is_correct_diagnosis=True, is_required=True).count()
    optional_correct = updated_options.filter(is_correct_diagnosis=True, is_required=False).count()
    high_interference = updated_options.filter(is_correct_diagnosis=False, interference_level=3).count()
    medium_interference = updated_options.filter(is_correct_diagnosis=False, interference_level=2).count()
    low_interference = updated_options.filter(is_correct_diagnosis=False, interference_level=1).count()
    
    print(f"  🔴 必选正确诊断: {required_correct} 个")
    print(f"  ⚪ 可选正确诊断: {optional_correct} 个")
    print(f"  🔴 高干扰选项: {high_interference} 个")
    print(f"  🟡 中干扰选项: {medium_interference} 个")
    print(f"  🟢 低干扰选项: {low_interference} 个")
    
    print(f"\n✨ 优化完成! 共更新 {updated_count} 个诊断选项")
    
    # 教学设计说明
    print(f"\n🎓 教学设计逻辑:")
    print(f"  1. 必选正确诊断 - 学生必须选中才算完全正确")
    print(f"  2. 高干扰选项 - 相似疾病，考验鉴别诊断能力")
    print(f"  3. 中/低干扰选项 - 不同程度的迷惑项，考验基础知识")
    print(f"  4. 难度分级 - 从容易排除到困难识别的渐进设计")
    
    return True


def create_diagnosis_migration():
    """创建数据库迁移文件"""
    
    print(f"\n🔄 创建数据库迁移...")
    
    try:
        import subprocess
        result = subprocess.run([
            'python', 'manage.py', 'makemigrations', 'cases', 
            '--name', 'optimize_diagnosis_options'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 迁移文件创建成功")
            print(f"💡 请运行 'python manage.py migrate' 应用迁移")
        else:
            print(f"❌ 迁移文件创建失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 创建迁移时出错: {str(e)}")


if __name__ == '__main__':
    optimize_diagnosis_options()
    create_diagnosis_migration()