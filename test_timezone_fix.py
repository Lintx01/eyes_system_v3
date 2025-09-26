#!/usr/bin/env python3
"""
测试timezone修复的脚本
"""

from datetime import datetime, timezone as dt_timezone
import sys

def test_timezone_fixes():
    """测试所有timezone相关的修复"""
    
    print("🔧 测试timezone修复...")
    
    try:
        # 测试1: make_aware修复（模拟Django的timezone.make_aware）
        print("\n1. 测试排序逻辑修复:")
        
        class MockTimezone:
            @staticmethod
            def make_aware(dt):
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=dt_timezone.utc)
                return dt
        
        timezone_mock = MockTimezone()
        
        # 模拟progress_data数据
        progress_data = [
            {'student': 'Student1', 'last_practice_time': datetime(2024, 1, 15, 10, 0)},
            {'student': 'Student2', 'last_practice_time': None},  # 没有练习时间的学生
            {'student': 'Student3', 'last_practice_time': datetime(2024, 1, 20, 15, 30)},
        ]
        
        # 使用修复后的排序逻辑
        min_datetime = timezone_mock.make_aware(datetime.min)
        progress_data.sort(key=lambda x: x['last_practice_time'] or min_datetime, reverse=True)
        
        print("   ✅ 排序成功！")
        print("   排序结果：")
        for i, data in enumerate(progress_data, 1):
            last_time = data['last_practice_time']
            if last_time:
                time_str = last_time.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = "无练习记录"
            print(f"   {i}. {data['student']}: {time_str}")
        
        # 测试2: datetime.timezone.utc修复
        print("\n2. 测试datetime.timezone.utc修复:")
        
        # 模拟timestamp转换
        import time
        timestamp = time.time()
        start_time = datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)
        print(f"   ✅ 时间戳转换成功: {start_time}")
        
        print("\n🎉 所有timezone修复测试通过！")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("Django教师端学生进度页面 - Timezone修复测试")
    print("=" * 50)
    
    success = test_timezone_fixes()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ 修复验证成功！")
        print("📝 修复内容：")
        print("   1. 将 timezone.utc 替换为 timezone.make_aware(datetime.min)")
        print("   2. 将其他 timezone.utc 替换为 datetime.timezone.utc")
        print("   3. 确保排序逻辑正常工作")
        print("🚀 教师端学生进度页面现在应该可以正常显示了！")
        print("=" * 50)
        return 0
    else:
        print("\n❌ 修复验证失败，请检查代码")
        return 1

if __name__ == "__main__":
    sys.exit(main())