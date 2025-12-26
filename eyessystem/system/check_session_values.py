import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import StudentClinicalSession

print("数据库中所有会话的状态值:\n")
sessions = StudentClinicalSession.objects.all()
print(f"总会话数: {sessions.count()}\n")

status_values = {}
for session in sessions:
    status = session.session_status
    if status not in status_values:
        status_values[status] = []
    status_values[status].append(f"{session.student.username} - {session.clinical_case.title}")

print("按状态分组:")
for status, sessions_list in status_values.items():
    print(f"\n状态值: '{status}' (数量: {len(sessions_list)})")
    for s in sessions_list:
        print(f"  - {s}")

print("\n\n正确的状态值应该是:")
correct_values = [
    'case_presentation',
    'examination_selection', 
    'examination_results',
    'diagnosis_reasoning',
    'treatment_selection',
    'learning_feedback',
    'completed'
]
for v in correct_values:
    print(f"  - {v}")
