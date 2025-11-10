#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复异常的学习时长数据
将超过合理范围的started_at时间修正为更接近completed_at的时间
"""

import os
import sys
import django
from datetime import timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession
from django.utils import timezone


def fix_abnormal_study_times():
    """修复异常的学习时长"""
    
    print("=== 修复异常学习时长数据 ===\n")
    
    MAX_HOURS = 4  # 单次学习最长4小时
    max_duration = timedelta(hours=MAX_HOURS)
    
    # 获取所有已完成的会话
    sessions = StudentClinicalSession.objects.filter(
        completed_at__isnull=False,
        started_at__isnull=False
    )
    
    print(f"📊 共找到 {sessions.count()} 个已完成的会话\n")
    
    fixed_count = 0
    total_before = 0
    total_after = 0
    
    for session in sessions:
        duration = session.completed_at - session.started_at
        duration_hours = duration.total_seconds() / 3600
        
        total_before += duration.total_seconds() / 60  # 分钟
        
        if duration > max_duration:
            print(f"🔧 修复会话: {session.clinical_case.case_id}")
            print(f"   学生: {session.student.username}")
            print(f"   原始时长: {duration_hours:.2f} 小时")
            print(f"   started_at: {session.started_at}")
            print(f"   completed_at: {session.completed_at}")
            
            # 尝试使用last_activity
            if session.last_activity and session.last_activity < session.completed_at:
                alt_duration = session.completed_at - session.last_activity
                if alt_duration < max_duration:
                    # 使用last_activity
                    session.started_at = session.last_activity
                    print(f"   ✅ 使用last_activity: {session.last_activity}")
                else:
                    # last_activity也太远，设置为completed_at前1小时
                    session.started_at = session.completed_at - timedelta(hours=1)
                    print(f"   ✅ 设置为完成前1小时")
            else:
                # 没有合适的last_activity，设置为completed_at前1小时
                session.started_at = session.completed_at - timedelta(hours=1)
                print(f"   ✅ 设置为完成前1小时")
            
            new_duration = session.completed_at - session.started_at
            new_hours = new_duration.total_seconds() / 3600
            print(f"   修正后时长: {new_hours:.2f} 小时\n")
            
            session.save()
            fixed_count += 1
            total_after += new_duration.total_seconds() / 60
        else:
            total_after += duration.total_seconds() / 60
    
    print("=" * 50)
    print(f"✅ 修复完成!")
    print(f"   修复会话数: {fixed_count}")
    print(f"   修复前总时长: {total_before:.1f} 分钟 ({total_before/60:.2f} 小时)")
    print(f"   修复后总时长: {total_after:.1f} 分钟 ({total_after/60:.2f} 小时)")
    print(f"   减少时长: {(total_before - total_after):.1f} 分钟 ({(total_before - total_after)/60:.2f} 小时)")
    
    if fixed_count > 0:
        print(f"\n💡 建议:")
        print(f"   1. 刷新学生进度页面查看修正后的学习时长")
        print(f"   2. 未来新数据会自动应用4小时上限保护")
        print(f"   3. 考虑添加实时活跃时间追踪以获得更准确的数据")


if __name__ == '__main__':
    fix_abnormal_study_times()
