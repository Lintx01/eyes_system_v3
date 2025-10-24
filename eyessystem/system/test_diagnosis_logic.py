#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试诊断提交逻辑
"""

import os
import sys
import django
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, DiagnosisOption, StudentClinicalSession
from django.contrib.auth.models import User
from django.test import RequestFactory
from cases.views import submit_diagnosis_choice


def test_diagnosis_logic():
    """测试诊断提交逻辑"""
    
    print("=== 测试诊断提交逻辑 ===\n")
    
    # 获取测试数据
    try:
        case = ClinicalCase.objects.first()
        user = User.objects.filter(is_staff=False).first()
        
        if not case or not user:
            print("❌ 缺少测试数据")
            return
            
        # 获取诊断选项
        diagnosis_options = DiagnosisOption.objects.filter(clinical_case=case)
        correct_options = diagnosis_options.filter(is_correct_diagnosis=True)
        wrong_options = diagnosis_options.filter(is_correct_diagnosis=False)
        
        print(f"📋 案例: {case.case_id}")
        print(f"✅ 正确诊断: {[d.diagnosis_name for d in correct_options]}")
        print(f"❌ 错误选项: {[d.diagnosis_name for d in wrong_options]}")
        
        # 重置会话
        session, _ = StudentClinicalSession.objects.get_or_create(
            student=user,
            clinical_case=case,
            defaults={'session_status': 'diagnosis'}
        )
        session.diagnosis_attempt_count = 0
        session.diagnosis_guidance_level = 0
        session.session_status = 'diagnosis'
        session.save()
        
        print(f"\n🔄 初始状态: 尝试次数={session.diagnosis_attempt_count}, 指导级别={session.diagnosis_guidance_level}")
        
        # 模拟不同的诊断尝试
        test_cases = [
            {
                'name': '第1次尝试 - 完全错误',
                'selected': [wrong_options.first().id] if wrong_options.exists() else []
            },
            {
                'name': '第2次尝试 - 部分正确',  
                'selected': [correct_options.first().id, wrong_options.first().id] if correct_options.exists() and wrong_options.exists() else []
            },
            {
                'name': '第3次尝试 - 完全正确',
                'selected': [d.id for d in correct_options]
            }
        ]
        
        factory = RequestFactory()
        
        for test_case in test_cases:
            if not test_case['selected']:
                continue
                
            print(f"\n--- {test_case['name']} ---")
            
            # 准备请求数据
            request_data = {
                'case_id': case.case_id,
                'selected_diagnosis_ids': test_case['selected']
            }
            
            # 创建模拟请求
            request = factory.post('/api/clinical/submit-diagnosis/', 
                                 data=json.dumps(request_data),
                                 content_type='application/json')
            request.user = user
            
            # 调用视图函数
            response = submit_diagnosis_choice(request)
            response_data = json.loads(response.content)
            
            print(f"选择诊断ID: {test_case['selected']}")
            print(f"响应成功: {response_data.get('success')}")
            
            if response_data.get('success'):
                data = response_data.get('data', {})
                print(f"当前阶段: {data.get('current_stage')}")
                print(f"尝试次数: {data.get('attempt_count')}")
                print(f"指导级别: {data.get('guidance_level')}")
                print(f"诊断得分: {data.get('diagnosis_score')}")
                print(f"反馈内容: {data.get('diagnosis_feedback')}")
                
                # 检查是否有诊断选项返回
                if 'diagnosis_options' in data:
                    print(f"返回诊断选项数量: {len(data['diagnosis_options'])}")
                else:
                    print("未返回诊断选项")
                    
            else:
                print(f"错误: {response_data.get('message')}")
                
            # 重新加载会话状态
            session.refresh_from_db()
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_diagnosis_logic()