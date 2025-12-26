"""统一前后端的阶段命名 - 全部使用后端的完整命名"""

file_path = 'cases/templates/student/clinical_case_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有前端的简短命名为后端的完整命名
replacements = [
    # currentStage 赋值
    ("clinicalSession.currentStage = 'history'", "clinicalSession.currentStage = 'case_presentation'"),
    ("clinicalSession.currentStage = 'examination'", "clinicalSession.currentStage = 'examination_selection'"),
    ("clinicalSession.currentStage = 'diagnosis'", "clinicalSession.currentStage = 'diagnosis_reasoning'"),
    ("clinicalSession.currentStage = 'treatment'", "clinicalSession.currentStage = 'treatment_selection'"),
    
    # currentStage 比较
    ("clinicalSession.currentStage === 'history'", "clinicalSession.currentStage === 'case_presentation'"),
    ("clinicalSession.currentStage === 'examination'", "clinicalSession.currentStage === 'examination_selection'"),
    ("clinicalSession.currentStage === 'diagnosis'", "clinicalSession.currentStage === 'diagnosis_reasoning'"),
    ("clinicalSession.currentStage === 'treatment'", "clinicalSession.currentStage === 'treatment_selection'"),
]

changed_count = 0
for old, new in replacements:
    count = content.count(old)
    if count > 0:
        print(f"替换: {old}")
        print(f"  -> {new}")
        print(f"  ({count}处)\n")
        content = content.replace(old, new)
        changed_count += count

if changed_count > 0:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ 总共修复了 {changed_count} 处前端阶段命名")
else:
    print("未找到需要修复的内容")
