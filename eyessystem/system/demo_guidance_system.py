#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
鉴别诊断智能指导系统演示
模拟学生的学习过程和系统的指导响应
"""

import json


def simulate_diagnosis_attempts():
    """模拟学生诊断尝试过程"""
    
    print("🎓 鉴别诊断智能指导系统 - 学习演示")
    print("=" * 50)
    
    # 模拟案例数据
    case_info = {
        'case_id': 'CC3676875A',
        'diagnosis': '高血压性视网膜病变',
        'correct_diagnoses': ['糖尿病视网膜病变', '视网膜动脉阻塞', '视网膜分支静脉阻塞'],
        'available_options': [
            '糖尿病视网膜病变',
            '视网膜动脉阻塞', 
            '视网膜分支静脉阻塞',
            '青光眼',
            '白内障',
            '黄斑变性'
        ]
    }
    
    print(f"📋 案例：{case_info['case_id']} - {case_info['diagnosis']}")
    print(f"✅ 正确鉴别诊断：{', '.join(case_info['correct_diagnoses'])}")
    print(f"🔍 可选诊断选项：{', '.join(case_info['available_options'])}")
    print()
    
    # 模拟学生尝试
    attempts = [
        {
            'attempt': 1,
            'selected': ['糖尿病视网膜病变', '青光眼'],
            'feedback_level': 1,
            'feedback': '您选择了1个正确诊断，但还有2个正确诊断未选择，同时选择了1个错误诊断。请重新思考并调整您的选择。\n\n💡 轻度提示：请仔细回顾患者的症状、体征和检查结果。',
            'score': 0,
            'status': '需要重新选择'
        },
        {
            'attempt': 2,
            'selected': ['糖尿病视网膜病变', '视网膜动脉阻塞', '白内障'],
            'feedback_level': 2,
            'feedback': '您选择了2个正确诊断，但还有1个正确诊断未选择，同时选择了1个错误诊断。\n\n⚠️ 中度提示：\n• 糖尿病视网膜病变: 微血管瘤、出血点和渗出物是典型表现\n• 白内障: 注意晶状体的透明度变化，该患者主要表现为视网膜病变',
            'score': 0,
            'status': '需要重新选择'
        },
        {
            'attempt': 3,
            'selected': ['糖尿病视网膜病变', '视网膜动脉阻塞', '视网膜分支静脉阻塞'],
            'feedback_level': 0,
            'feedback': '恭喜！您的鉴别诊断完全正确！（第3次尝试，得分：80分）',
            'score': 80,
            'status': '进入治疗阶段'
        }
    ]
    
    for attempt_data in attempts:
        print(f"🔄 第{attempt_data['attempt']}次尝试")
        print("-" * 30)
        print(f"学生选择：{', '.join(attempt_data['selected'])}")
        print()
        print("系统反馈：")
        print(attempt_data['feedback'])
        print()
        print(f"📊 得分：{attempt_data['score']}分")
        print(f"📌 状态：{attempt_data['status']}")
        
        if attempt_data['attempt'] < len(attempts):
            print()
            print("🔄 学生可以重新选择...")
            print("=" * 50)
        else:
            print()
            print("🎉 学习完成！进入治疗决策阶段。")
    
    print()
    print("🎯 智能指导系统特点：")
    print("• 🎓 循序渐进：根据尝试次数提供不同深度的指导")
    print("• 🔄 允许重试：鼓励学生从错误中学习")
    print("• 📊 动态评分：基于尝试次数调整最终得分")
    print("• 💡 个性化：避免直接给出答案，培养思维能力")
    print()
    print("✨ 教学目标达成：学生通过多次尝试掌握正确的诊断思路！")


def show_guidance_levels():
    """展示三级指导体系"""
    
    print("\n📚 三级智能指导体系详解")
    print("=" * 40)
    
    levels = [
        {
            'level': 1,
            'name': '轻度提示',
            'color': '🟢',
            'trigger': '第1次错误',
            'purpose': '引导思考方向',
            'example': '结合患者的糖尿病病史和眼底检查'
        },
        {
            'level': 2,
            'name': '中度提示', 
            'color': '🟡',
            'trigger': '第2次错误',
            'purpose': '提供临床特征',
            'example': '微血管瘤、出血点和渗出物是糖尿病视网膜病变的典型表现'
        },
        {
            'level': 3,
            'name': '强提示',
            'color': '🔴', 
            'trigger': '第3次及以上错误',
            'purpose': '详细诊断依据',
            'example': '该患者有糖尿病史，眼底可见微血管瘤、出血和硬性渗出，诊断为糖尿病视网膜病变'
        }
    ]
    
    for level_data in levels:
        print(f"{level_data['color']} **级别{level_data['level']} - {level_data['name']}**")
        print(f"   触发条件：{level_data['trigger']}")
        print(f"   指导目的：{level_data['purpose']}")
        print(f"   示例内容：{level_data['example']}")
        print()


if __name__ == '__main__':
    simulate_diagnosis_attempts()
    show_guidance_levels()
    
    print("🚀 系统现已准备就绪，可以为学生提供智能诊断指导！")