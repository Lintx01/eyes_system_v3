"""
测试诊断评分逻辑
"""

# 模拟评分计算
def calculate_diagnosis_score(attempt_count):
    """计算诊断得分"""
    return max(100 - (attempt_count - 1) * 10, 60)

print("=" * 60)
print("诊断评分测试")
print("=" * 60)

print("\n场景1: 提交前 attempt_count=0，提交后+1变成1")
attempt_count = 0
attempt_count += 1  # 提交时增加
score = calculate_diagnosis_score(attempt_count)
print(f"尝试次数: {attempt_count}, 得分: {score}")
print(f"期望: 第1次尝试应该得100分")
print(f"结果: {'✓ 正确' if score == 100 else '✗ 错误'}")

print("\n场景2: 提交前 attempt_count=1，提交后+1变成2")
attempt_count = 1
attempt_count += 1  # 再次提交
score = calculate_diagnosis_score(attempt_count)
print(f"尝试次数: {attempt_count}, 得分: {score}")
print(f"期望: 第2次尝试应该得90分")
print(f"结果: {'✓ 正确' if score == 90 else '✗ 错误'}")

print("\n场景3: 多次尝试")
for i in range(1, 8):
    score = calculate_diagnosis_score(i)
    print(f"第{i}次尝试: {score}分")

print("\n" + "=" * 60)

# 检查实际数据
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession, TeachingFeedback

print("\n检查student3的第1次诊断反馈:")
session = StudentClinicalSession.objects.get(id=11)
first_feedback = TeachingFeedback.objects.filter(
    student_session=session,
    feedback_stage='diagnosis'
).order_by('created_at').first()

if first_feedback:
    print(f"反馈内容: {first_feedback.feedback_content}")
    print(f"反馈时间: {first_feedback.created_at}")
    
    # 分析
    if "首次尝试即正确" in first_feedback.feedback_content:
        print("✓ 反馈消息包含首次成功提示")
    elif "第" in first_feedback.feedback_content and "次尝试" in first_feedback.feedback_content:
        print("⚠ 反馈显示为非首次尝试")
    else:
        print("⚠ 反馈没有显示尝试次数信息")

print("\n" + "=" * 60)
