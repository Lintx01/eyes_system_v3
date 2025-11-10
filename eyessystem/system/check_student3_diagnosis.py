"""
检查student3的诊断记录
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession, TeachingFeedback

session = StudentClinicalSession.objects.filter(student__username='student3').order_by('-id').first()

print(f"会话ID: {session.id}")
print(f"病例: {session.clinical_case.title}")
print(f"诊断尝试次数: {session.diagnosis_attempt_count}")
print(f"诊断得分: {session.diagnosis_score}")

feedbacks = TeachingFeedback.objects.filter(
    student_session=session, 
    feedback_stage='diagnosis'
).order_by('created_at')

print(f"\n诊断阶段反馈记录 (共{feedbacks.count()}条):")
for i, fb in enumerate(feedbacks, 1):
    print(f"\n第{i}次提交:")
    print(f"  时间: {fb.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  类型: {fb.feedback_type}")
    print(f"  反馈内容: {fb.feedback_content[:200]}")
