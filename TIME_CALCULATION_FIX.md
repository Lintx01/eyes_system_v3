# 学习时长计算问题分析与修复方案

## 🐛 问题根源

### 当前实现（第290-303行）
```python
# 计算总学习时长（分钟）
total_study_time = 0
for session in user_sessions.filter(completed_at__isnull=False):
    if session.completed_at and session.started_at:
        duration = session.completed_at - session.started_at
        total_study_time += duration.total_seconds() / 60
```

### 问题所在：
1. **`started_at` 使用 `auto_now_add=True`** 
   - 在数据库中创建记录时自动设置
   - 如果学生创建会话后离开，几天后再回来完成，时间差会非常大
   
2. **`last_activity` 使用 `auto_now=True`**
   - 每次保存记录时自动更新
   - 不能准确反映真实学习时间

3. **示例场景导致100小时错误：**
   ```
   2025-01-01 10:00:00  创建会话 (started_at)
   2025-01-05 14:00:00  完成会话 (completed_at)
   时间差 = 4天4小时 = 100小时！
   ```

## ✅ 修复方案

### 方案1：使用 last_activity 替代 started_at（推荐）
```python
# 修改计算逻辑，使用last_activity（最后活动时间）
total_study_time = 0
for session in user_sessions.filter(completed_at__isnull=False):
    if session.completed_at and session.last_activity:
        # 使用last_activity到completed_at的时间差
        # last_activity会在每次操作时更新，更接近真实完成时间
        duration = session.completed_at - session.last_activity
        # 设置合理上限（单次学习不超过4小时）
        duration_minutes = min(duration.total_seconds() / 60, 240)
        total_study_time += duration_minutes
```

### 方案2：添加最大时长限制（简单快速）
```python
# 在现有代码基础上添加上限
total_study_time = 0
MAX_SESSION_HOURS = 4  # 单次学习最长4小时
for session in user_sessions.filter(completed_at__isnull=False):
    if session.completed_at and session.started_at:
        duration = session.completed_at - session.started_at
        duration_minutes = duration.total_seconds() / 60
        # 限制单次学习时长
        duration_minutes = min(duration_minutes, MAX_SESSION_HOURS * 60)
        total_study_time += duration_minutes
```

### 方案3：使用time_spent字段（最准确，需额外开发）
```python
# 使用已有的time_spent JSON字段记录精确时间
total_study_time = 0
for session in user_sessions.filter(completed_at__isnull=False):
    if session.time_spent:
        # time_spent是JSON字段，记录各阶段真实用时
        for stage, minutes in session.time_spent.items():
            total_study_time += minutes
```

## 🔧 立即修复步骤

### 1. 修复计算代码（views.py 第297-303行）

替换现有代码为：

```python
# 计算总学习时长（分钟）- 修复版本
total_study_time = 0
MAX_SESSION_MINUTES = 240  # 单次最长4小时

for session in user_sessions.filter(completed_at__isnull=False):
    if session.completed_at and session.started_at:
        duration = session.completed_at - session.started_at
        duration_minutes = duration.total_seconds() / 60
        
        # 应用合理上限，防止异常数据
        if duration_minutes > MAX_SESSION_MINUTES:
            # 如果超过上限，使用last_activity时间
            if session.last_activity:
                alt_duration = session.completed_at - session.last_activity
                duration_minutes = min(alt_duration.total_seconds() / 60, MAX_SESSION_MINUTES)
            else:
                duration_minutes = MAX_SESSION_MINUTES
        
        total_study_time += duration_minutes

total_study_time = round(total_study_time)
```

### 2. 清理异常数据（可选）

创建管理命令修正历史异常数据：

```python
# management/commands/fix_study_time.py
from django.core.management.base import BaseCommand
from cases.models import StudentClinicalSession
from datetime import timedelta

class Command(BaseCommand):
    def handle(self, *args, **options):
        MAX_HOURS = 4
        sessions = StudentClinicalSession.objects.filter(
            completed_at__isnull=False
        )
        
        fixed_count = 0
        for session in sessions:
            if session.completed_at and session.started_at:
                duration = session.completed_at - session.started_at
                if duration > timedelta(hours=MAX_HOURS):
                    # 修正为last_activity
                    if session.last_activity:
                        session.started_at = session.last_activity - timedelta(hours=1)
                        session.save()
                        fixed_count += 1
        
        self.stdout.write(f'修复了 {fixed_count} 个异常会话')
```

## 📊 验证修复

运行诊断脚本验证：
```bash
python diagnose_time_issue.py
```

预期输出应该显示所有会话时长都在合理范围内（0-4小时）。

## 🎯 长期改进建议

1. **实时记录活跃时间**：添加心跳机制，每隔30秒记录用户活动
2. **使用time_spent字段**：精确记录每个阶段的真实用时
3. **添加暂停/继续功能**：允许学生暂停学习，不计入时间
4. **数据验证**：在保存时验证时间合理性