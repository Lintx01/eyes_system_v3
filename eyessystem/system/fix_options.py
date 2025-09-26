"""
数据修复脚本 - 确保练习题选项包含正确的字母前缀
使用方法：python manage.py shell < fix_options.py
"""

from cases.models import Exercise
import json

def fix_exercise_options():
    """修复练习题选项格式，确保包含字母前缀"""
    exercises = Exercise.objects.all()
    
    for exercise in exercises:
        options = exercise.get_options_list()
        if not options:
            continue
            
        # 检查是否已经包含字母前缀
        needs_prefix = True
        if options and len(options) > 0:
            first_option = options[0].strip()
            if first_option.startswith('A.') or first_option.startswith('a.'):
                needs_prefix = False
                
        if needs_prefix:
            # 添加字母前缀
            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            new_options = []
            for i, option in enumerate(options):
                if i < len(letters):
                    new_options.append(f"{letters[i]}. {option.strip()}")
                else:
                    new_options.append(f"{i+1}. {option.strip()}")
            
            # 更新数据库
            exercise.options = json.dumps(new_options, ensure_ascii=False)
            exercise.save()
            print(f"✓ 修复题目: {exercise.question[:50]}...")
        else:
            print(f"- 跳过题目: {exercise.question[:50]}... (已有前缀)")

if __name__ == "__main__":
    print("开始修复练习题选项格式...")
    fix_exercise_options()
    print("修复完成！")