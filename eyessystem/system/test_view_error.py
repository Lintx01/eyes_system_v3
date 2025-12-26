#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试临床病例详情页视图是否有错误"""

import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from cases.models import ClinicalCase
from cases.views import clinical_case_detail

User = get_user_model()

def test_clinical_case_detail():
    """测试临床病例详情页"""
    try:
        # 获取测试病例
        case = ClinicalCase.objects.filter(case_id='CCC7D361F8').first()
        if not case:
            print("❌ 找不到病例 CCC7D361F8")
            return
        
        print(f"✓ 找到病例: {case.chief_complaint}")
        
        # 创建测试请求
        factory = RequestFactory()
        request = factory.get(f'/student/clinical/{case.case_id}/')
        
        # 获取一个学生用户
        student = User.objects.filter(role='student').first()
        if not student:
            print("❌ 找不到学生用户")
            return
        
        print(f"✓ 找到学生用户: {student.username}")
        request.user = student
        
        # 调用视图
        print("\n正在调用视图函数...")
        response = clinical_case_detail(request, case.case_id)
        
        print(f"\n✓ 视图执行成功!")
        print(f"  状态码: {response.status_code}")
        print(f"  响应类型: {type(response)}")
        
        if response.status_code != 200:
            print(f"\n⚠ 警告: 状态码不是200")
            if hasattr(response, 'content'):
                print(f"响应内容: {response.content[:500]}")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        print("\n完整错误堆栈:")
        traceback.print_exc()

if __name__ == '__main__':
    test_clinical_case_detail()
