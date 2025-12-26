"""批量替换views.py中的错误session_status值"""

file_path = 'cases/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有错误的状态值
replacements = [
    ("'session_status': 'history'", "'session_status': 'case_presentation'"),
    ("session.session_status = 'history'", "session.session_status = 'case_presentation'"),
    ("session.session_status = 'diagnosis'", "session.session_status = 'diagnosis_reasoning'"),
    ("session.session_status = 'treatment'", "session.session_status = 'treatment_selection'"),
]

changed_count = 0
for old, new in replacements:
    count = content.count(old)
    if count > 0:
        print(f"替换: {old} -> {new} ({count}处)")
        content = content.replace(old, new)
        changed_count += count

if changed_count > 0:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✓ 总共修复了 {changed_count} 处错误的状态值")
else:
    print("未找到需要修复的内容")
