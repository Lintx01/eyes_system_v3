#!/usr/bin/env python
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from cases.models import ClinicalCase
from cases.views import teacher_clinical_case_delete, is_teacher

print("=== 删除功能完整诊断 ===")

# 1. 检查案例存在
print("\n1. 检查案例数据:")
cases = ClinicalCase.objects.all()
print(f"   总案例数: {cases.count()}")
for case in cases:
    print(f"   - {case.case_id}: {case.title}")

if cases.count() == 0:
    print("   ❌ 没有案例可供测试")
    exit(1)

test_case = cases.first()
print(f"   ✅ 使用测试案例: {test_case.case_id}")

# 2. 检查URL路由
print("\n2. 检查URL路由:")
try:
    delete_url = reverse('teacher_clinical_case_delete', kwargs={'case_id': test_case.case_id})
    print(f"   ✅ 删除URL生成成功: {delete_url}")
    
    # 检查URL解析
    resolver = resolve(delete_url)
    print(f"   ✅ URL解析成功: {resolver.func.__name__}")
except Exception as e:
    print(f"   ❌ URL问题: {e}")

# 3. 检查用户权限
print("\n3. 检查用户权限:")
admin_user = User.objects.filter(is_superuser=True).first()
if admin_user:
    print(f"   用户: {admin_user.username}")
    print(f"   是否为教师: {is_teacher(admin_user)}")
    print(f"   是否为超级用户: {admin_user.is_superuser}")
    print(f"   ✅ 用户权限正常")
else:
    print("   ❌ 没有找到可用的管理员用户")

# 4. 测试视图访问
print("\n4. 测试视图访问:")
client = Client()
client.force_login(admin_user)

# 测试GET请求（删除确认页面）
try:
    response = client.get(delete_url)
    print(f"   GET请求状态码: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ 删除确认页面可以正常访问")
        content = response.content.decode()
        if 'confirm_delete' in content:
            print("   ✅ 确认页面包含确认复选框")
        if 'csrfmiddlewaretoken' in content:
            print("   ✅ 确认页面包含CSRF token")
    else:
        print(f"   ❌ GET请求失败: {response.status_code}")
        print(f"   响应内容: {response.content.decode()[:200]}")
except Exception as e:
    print(f"   ❌ GET请求异常: {e}")

# 5. 测试POST请求（实际删除）
print("\n5. 测试POST请求:")
initial_count = ClinicalCase.objects.count()
try:
    response = client.post(delete_url, {
        'confirm_delete': 'on'
    })
    print(f"   POST请求状态码: {response.status_code}")
    
    if response.status_code == 302:  # 重定向表示成功
        print("   ✅ POST请求成功（重定向）")
        print(f"   重定向到: {response['Location']}")
        
        # 检查是否真的删除了
        final_count = ClinicalCase.objects.count()
        if final_count < initial_count:
            print(f"   ✅ 删除成功！案例数从 {initial_count} 减少到 {final_count}")
        else:
            print(f"   ❌ 删除失败！案例数仍为 {final_count}")
    else:
        print(f"   ❌ POST请求失败: {response.status_code}")
        content = response.content.decode()
        print(f"   响应内容前200字符: {content[:200]}")
        if 'error' in content.lower():
            print("   可能包含错误信息")
            
except Exception as e:
    print(f"   ❌ POST请求异常: {e}")
    import traceback
    traceback.print_exc()

# 6. 总结
print("\n=== 诊断结果总结 ===")
final_case_count = ClinicalCase.objects.count()
print(f"最终案例数量: {final_case_count}")

if final_case_count < initial_count:
    print("🎉 删除功能工作正常！")
else:
    print("❌ 删除功能存在问题，需要进一步调试")