# 眼科教学系统 - 考试模块部署指南

## 1. 数据库迁移

### 步骤 1: 生成迁移文件
```bash
cd G:\AAA_眼科教学软件\eyes_system\eyessystem\system
python manage.py makemigrations cases
```

### 步骤 2: 应用迁移
```bash
python manage.py migrate
```

### 步骤 3: 验证迁移
```bash
python manage.py showmigrations cases
```

## 2. 系统初始化

### 步骤 1: 创建超级管理员
```bash
python manage.py createsuperuser
```

### 步骤 2: 初始化用户组和权限
```bash
python manage.py init_system
```

这个命令会自动创建：
- Teachers 用户组（教师）
- Students 用户组（学生）
- 分配相应的权限

### 步骤 3: 创建测试数据（可选）
```bash
python manage.py shell
```

然后在 Python shell 中执行：
```python
from django.contrib.auth.models import User, Group
from cases.models import Case, Exercise, Exam
from datetime import datetime, timedelta
from django.utils import timezone

# 创建教师用户
teacher_group = Group.objects.get(name='Teachers')
teacher = User.objects.create_user(
    username='teacher1',
    password='password123',
    email='teacher@example.com',
    first_name='张',
    last_name='教师'
)
teacher.groups.add(teacher_group)

# 创建学生用户
student_group = Group.objects.get(name='Students')
for i in range(5):
    student = User.objects.create_user(
        username=f'student{i+1}',
        password='password123',
        email=f'student{i+1}@example.com',
        first_name=f'学生{i+1}',
        last_name='同学'
    )
    student.groups.add(student_group)
```

## 3. 静态文件配置

### 步骤 1: 收集静态文件
```bash
python manage.py collectstatic
```

### 步骤 2: 确保媒体文件目录存在
```bash
mkdir -p media/case_images
mkdir -p media/exam_files
```

## 4. 导入示例病例（如果存在 sample_cases.csv）

```bash
python manage.py shell
```

```python
import csv
from cases.models import Case, Exercise

def import_sample_cases():
    with open('sample_cases.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            case = Case.objects.create(
                title=row['title'],
                description=row['description'],
                difficulty=row.get('difficulty', 'medium'),
                case_type=row.get('case_type', 'clinical'),
            )
            
            # 创建示例练习题
            Exercise.objects.create(
                case=case,
                question=f"关于{case.title}，以下描述正确的是？",
                question_type='single',
                options="A. 选项A\nB. 选项B\nC. 选项C\nD. 选项D",
                correct_answer="A",
                explanation="这是正确答案的解析..."
            )

import_sample_cases()
```

## 5. 权限验证

### 验证教师权限：
1. 登录教师账号
2. 访问 `/teacher/dashboard/`
3. 尝试创建考试、查看成绩等功能

### 验证学生权限：
1. 登录学生账号
2. 访问 `/student/dashboard/`
3. 尝试参与考试、查看成绩等功能

## 6. 功能测试清单

### 学生功能测试：
- [ ] 查看考试列表
- [ ] 开始考试
- [ ] 答题过程（倒计时、防作弊）
- [ ] 提交考试
- [ ] 查看考试结果
- [ ] 查看错题解析

### 教师功能测试：
- [ ] 创建考试
- [ ] 选择题目和参与学生
- [ ] 查看考试列表
- [ ] 查看学生成绩
- [ ] 导出成绩Excel
- [ ] 查看学习数据统计

### 系统功能测试：
- [ ] 自动评分算法
- [ ] 考试时间控制
- [ ] 权限控制
- [ ] 数据统计准确性

## 7. 常见问题解决

### 问题 1: 迁移失败
```bash
# 删除迁移文件后重新生成
rm cases/migrations/0*.py
python manage.py makemigrations cases
python manage.py migrate
```

### 问题 2: 静态文件无法加载
确保 settings.py 中配置正确：
```python
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

### 问题 3: 权限不足
重新运行初始化命令：
```bash
python manage.py init_system
```

## 8. 生产环境部署建议

### 安全设置：
1. 修改 `DEBUG = False`
2. 设置合适的 `ALLOWED_HOSTS`
3. 使用环境变量管理敏感信息
4. 配置 HTTPS

### 性能优化：
1. 配置数据库连接池
2. 启用缓存机制
3. 优化静态文件服务
4. 配置日志记录

### 备份策略：
1. 定期备份数据库
2. 备份媒体文件
3. 备份配置文件

## 9. 系统维护

### 定期清理：
```bash
# 清理过期的考试记录（可选）
python manage.py shell -c "
from cases.models import ExamRecord
from datetime import datetime, timedelta
from django.utils import timezone

# 删除6个月前的考试记录（根据需要调整）
cutoff_date = timezone.now() - timedelta(days=180)
old_records = ExamRecord.objects.filter(created_at__lt=cutoff_date)
print(f'将删除 {old_records.count()} 条过期记录')
# old_records.delete()  # 取消注释以执行删除
"
```

### 数据统计更新：
```bash
# 更新学习进度统计（可以设置为定时任务）
python manage.py shell -c "
from cases.models import UserProgress, ExamRecord
from django.contrib.auth.models import User

# 重新计算所有用户的学习进度
for user in User.objects.filter(groups__name='Students'):
    # 这里可以添加进度重新计算的逻辑
    pass
"
```

## 10. 技术支持

如遇到问题，请检查：
1. Django 版本兼容性
2. 数据库连接状态
3. 静态文件配置
4. 用户权限设置
5. 模板文件路径

系统开发完成！请按照以上步骤进行部署和测试。