#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断学习时长计算问题
"""

import os
import sys
import django
from datetime import datetime, timedelta

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession
from django.contrib.auth.models import User


def diagnose_time_calculation():
    """诊断时间计算问题"""
    
    print("=== 学习时长计算问题诊断 ===\n")
    
    # 获取学生用户
    student = User.objects.filter(is_staff=False).first()
    if not student:
        print("❌ 没有找到学生用户")
        return
    
    print(f"👤 学生: {student.username}\n")
    
    # 获取所有会话
    sessions = StudentClinicalSession.objects.filter(student=student).order_by('-created_at')
    
    if not sessions.exists():
        print("❌ 没有找到学习会话")
        return
    
    print(f"📊 共找到 {sessions.count()} 个学习会话\n")
    
    total_calculated_minutes = 0
    problem_sessions = []
    
    for i, session in enumerate(sessions, 1):
        print(f"--- 会话 #{i} ---")
        print(f"案例: {session.clinical_case.case_id}")
        print(f"状态: {session.session_status}")
        print(f"创建时间: {session.created_at}")
        print(f"开始时间: {session.start_time}")
        print(f"结束时间: {session.end_time}")
        print(f"更新时间: {session.updated_at}")
        
        if session.end_time and session.start_time:
            duration = session.end_time - session.start_time
            duration_minutes = duration.total_seconds() / 60
            duration_hours = duration_minutes / 60
            
            print(f"⏱️ 计算时长: {duration}")
            print(f"   = {duration_minutes:.2f} 分钟")
            print(f"   = {duration_hours:.2f} 小时")
            
            total_calculated_minutes += duration_minutes
            
            # 检查异常情况
            if duration_minutes > 120:  # 超过2小时
                problem_sessions.append({
                    'session': session,
                    'duration_hours': duration_hours,
                    'issue': '时长异常（超过2小时）'
                })
                print(f"⚠️ 警告: 学习时长异常！")
            
            if duration_minutes < 0:  # 负数时长
                problem_sessions.append({
                    'session': session,
                    'duration_hours': duration_hours,
                    'issue': '时长为负数'
                })
                print(f"❌ 错误: 时长为负数！")
                
            # 检查时间是否合理
            if session.start_time > session.end_time:
                problem_sessions.append({
                    'session': session,
                    'duration_hours': duration_hours,
                    'issue': '开始时间晚于结束时间'
                })
                print(f"❌ 错误: 开始时间晚于结束时间！")
        else:
            print(f"ℹ️ 未完成（没有结束时间）")
            
            # 检查是否start_time也是None
            if session.start_time is None:
                print(f"⚠️ 警告: start_time为空")
            else:
                # 计算从开始到现在的时间
                now_duration = datetime.now(session.start_time.tzinfo) - session.start_time
                now_minutes = now_duration.total_seconds() / 60
                print(f"   从开始到现在: {now_minutes:.2f} 分钟")
        
        print()
    
    # 汇总
    print("="*50)
    print(f"📈 总计算时长: {total_calculated_minutes:.2f} 分钟")
    print(f"              = {total_calculated_minutes/60:.2f} 小时")
    
    if problem_sessions:
        print(f"\n⚠️ 发现 {len(problem_sessions)} 个问题会话:")
        for i, ps in enumerate(problem_sessions, 1):
            print(f"\n问题 #{i}:")
            print(f"  案例: {ps['session'].clinical_case.case_id}")
            print(f"  问题: {ps['issue']}")
            print(f"  异常时长: {ps['duration_hours']:.2f} 小时")
            print(f"  开始: {ps['session'].start_time}")
            print(f"  结束: {ps['session'].end_time}")
    
    # 分析可能的原因
    print("\n🔍 可能的问题原因:")
    print("1. end_time被错误设置为很晚的时间")
    print("2. start_time和end_time没有在正确的时机更新")
    print("3. 时区问题导致时间计算错误")
    print("4. 用户长时间没有关闭页面，导致时间一直累积")
    
    # 给出修复建议
    print("\n💡 修复建议:")
    print("1. 只在用户真正完成学习时设置end_time")
    print("2. 使用created_at和updated_at的差值作为参考")
    print("3. 添加最大学习时长限制（如单次不超过2小时）")
    print("4. 记录详细的时间戳日志便于追踪")
    print("5. 考虑使用活动时间而非总时间（排除离开时间）")


if __name__ == '__main__':
    diagnose_time_calculation()