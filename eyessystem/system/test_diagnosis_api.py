"""测试诊断选项API"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from cases.diagnosis_views import get_diagnosis_options

User = get_user_model()

# 创建测试请求
factory = RequestFactory()
request = factory.get('/api/clinical/case/CCC7D361F8/diagnosis-options/')

# 获取一个非staff用户（学生）
try:
    student = User.objects.filter(is_staff=False, is_superuser=False).first()
    if not student:
        print("错误：没有找到学生用户")
        exit(1)
    
    request.user = student
    print(f"使用学生用户: {student.username}")
    
    # 调用API
    print("\n调用 get_diagnosis_options('CCC7D361F8')...")
    response = get_diagnosis_options(request, 'CCC7D361F8')
    
    print(f"\n响应状态码: {response.status_code}")
    print(f"响应内容: {response.content.decode('utf-8')}")
    
except Exception as e:
    import traceback
    print(f"\n错误: {str(e)}")
    print(f"\n完整错误追踪:")
    traceback.print_exc()
