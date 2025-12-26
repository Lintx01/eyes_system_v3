"""测试聊天API是否允许case_presentation阶段的聊天"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from cases.models import ClinicalCase
from cases.views import chat_api
import json

User = get_user_model()

# 创建请求工厂
factory = RequestFactory()

# 获取学生用户
student = User.objects.filter(username='student1').first()
print(f"测试用户: {student.username}")

# 获取病例
case_id = 'CCC7D361F8'
case = ClinicalCase.objects.get(case_id=case_id)
print(f"测试病例: {case.case_id} - {case.title}")

# 创建POST请求
request_data = {'message': '什么时候开始的？'}
request = factory.post(
    f'/api/clinical/case/{case_id}/chat/',
    data=json.dumps(request_data),
    content_type='application/json'
)
request.user = student

# 调用chat_api
print(f"\n发送聊天请求: {request_data['message']}")
response = chat_api(request, case_id)

# 解析响应
response_data = json.loads(response.content)
print(f"\n响应状态码: {response.status_code}")
print(f"响应内容: {json.dumps(response_data, ensure_ascii=False, indent=2)}")

if response_data.get('success'):
    print("\n✅ 聊天请求成功!")
else:
    print(f"\n❌ 聊天请求失败: {response_data.get('error')}")
