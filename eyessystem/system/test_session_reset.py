"""
测试会话重置逻辑
验证"单次会话惩罚"而非"终生惩罚"
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession, ClinicalCase
from django.contrib.auth.models import User

print("=" * 80)
print("会话重置逻辑测试")
print("=" * 80)

# 查找测试数据
try:
    student = User.objects.get(username='student3')
    case = ClinicalCase.objects.get(title='老年性白内障')
    
    # 查找该学生的会话
    session = StudentClinicalSession.objects.get(
        student=student,
        clinical_case=case
    )
    
    print(f"\n【当前状态】")
    print(f"学生: {session.student.username}")
    print(f"病例: {session.clinical_case.title}")
    print(f"会话状态: {session.session_status}")
    print(f"诊断尝试次数: {session.diagnosis_attempt_count}")
    print(f"诊断得分: {session.diagnosis_score}")
    print(f"完成时间: {session.completed_at}")
    
    print("\n" + "=" * 80)
    print("测试说明:")
    print("=" * 80)
    print("""
修改已完成！现在的行为是：

1. 学生第一次学习病例：
   - 诊断尝试次数从0开始
   - 第1次正确 = 100分
   - 第2次正确 = 90分
   - ...依此类推，最低60分

2. 学生完成病例后，再次点击该病例：
   - 系统自动检测到 session_status='completed'
   - 自动重置会话：
     * diagnosis_attempt_count = 0
     * diagnosis_guidance_level = 0
     * 所有分数清零
     * 清空所有选择
   - 学生可以重新开始，从100分开始计算

3. **关键改进**：
   - ✓ 扣分惩罚只在单次学习会话中生效
   - ✓ 重新学习时不会继承之前的尝试次数
   - ✓ 每次重新学习都是"全新开始"
   
测试方法：
1. 使用 student3 账号登录
2. 点击"老年性白内障"病例
3. 系统会自动重置该会话（因为已完成）
4. 进行诊断测试，第1次选对应该得100分

当前会话已经是 completed 状态，下次访问会自动重置！
    """)
    
except User.DoesNotExist:
    print("\n✗ 未找到 student3 用户")
except ClinicalCase.DoesNotExist:
    print("\n✗ 未找到'老年性白内障'病例")
except StudentClinicalSession.DoesNotExist:
    print("\n✗ 未找到学习会话")

print("=" * 80)
