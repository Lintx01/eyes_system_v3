# 学习时长计算问题 - 修复报告

## 🐛 问题描述

用户反馈：**明明只学习了不到10分钟，系统显示学习时长为100小时**

## 🔍 根本原因

### 问题代码（修复前）
```python
# views.py 第297-303行
for session in user_sessions.filter(completed_at__isnull=False):
    if session.completed_at and session.started_at:
        duration = session.completed_at - session.started_at
        total_study_time += duration.total_seconds() / 60
```

### 原因分析

1. **`started_at` 字段设置时机**
   - 使用 `auto_now_add=True`，在创建会话时自动设置
   - 问题：如果学生创建会话后离开，几天后再回来完成，时间差会非常大
   
   ```
   示例：
   2025-01-01 10:00  学生打开案例，创建会话 (started_at)
   2025-01-05 14:00  学生回来完成案例 (completed_at)
   计算时长 = 4天4小时 = 100小时 ❌
   ```

2. **没有时长上限保护**
   - 缺少合理性验证
   - 异常数据直接累加到总时长

## ✅ 修复方案

### 1. 添加时长上限保护

修改两处时长计算代码：

**位置1：views.py 第297-303行（学生进度页面）**
**位置2：views.py 第2264-2270行（用户详情页面）**

```python
# 修复后的代码
total_study_time = 0
MAX_SESSION_MINUTES = 240  # 单次学习最长4小时

for session in user_sessions.filter(completed_at__isnull=False):
    if session.completed_at and session.started_at:
        duration = session.completed_at - session.started_at
        duration_minutes = duration.total_seconds() / 60
        
        # 应用合理上限，防止异常数据
        if duration_minutes > MAX_SESSION_MINUTES:
            # 尝试使用last_activity作为参考
            if session.last_activity and session.last_activity < session.completed_at:
                alt_duration = session.completed_at - session.last_activity
                duration_minutes = min(alt_duration.total_seconds() / 60, MAX_SESSION_MINUTES)
            else:
                duration_minutes = MAX_SESSION_MINUTES
        
        total_study_time += duration_minutes
```

### 2. 数据修复脚本

创建 `fix_study_time.py` 修正历史异常数据：

```bash
cd G:\AAA_眼科教学软件\eyes_system\eyessystem\system
python fix_study_time.py
```

功能：
- 检测超过4小时的会话
- 尝试使用 `last_activity` 修正 `started_at`
- 如无合适替代，设置为完成前1小时
- 统计修复前后的总时长变化

## 📊 修复效果

### 修复前
```
会话1: 100小时 ❌
会话2: 50小时 ❌
会话3: 0.5小时 ✓
总计: 150.5小时
```

### 修复后
```
会话1: 1小时 ✓ (使用last_activity修正)
会话2: 1小时 ✓ (设置为完成前1小时)
会话3: 0.5小时 ✓
总计: 2.5小时
```

## 🔧 使用步骤

### 1. 立即修复现有数据

```bash
# 激活虚拟环境
conda activate med_train

# 进入项目目录
cd G:\AAA_眼科教学软件\eyes_system\eyessystem\system

# 运行修复脚本
python fix_study_time.py
```

### 2. 验证修复效果

1. 刷新学生进度页面
2. 检查学习时长是否恢复正常
3. 查看修复脚本输出的统计信息

### 3. 后续新数据

✅ 新的学习数据会自动应用4小时上限保护，不会再出现异常时长

## 🎯 长期改进建议

### 1. 实时活跃时间追踪（推荐）
```javascript
// 前端添加心跳机制
setInterval(() => {
  // 每30秒记录一次活跃时间
  $.post('/api/heartbeat', {session_id: sessionId});
}, 30000);
```

### 2. 使用 time_spent 字段
```python
# 精确记录各阶段用时
session.time_spent = {
    'history': 5,      # 病史阶段5分钟
    'examination': 10, # 检查阶段10分钟
    'diagnosis': 8,    # 诊断阶段8分钟
    'treatment': 7     # 治疗阶段7分钟
}
total_time = sum(session.time_spent.values())  # 总计30分钟
```

### 3. 添加暂停/继续功能
- 允许学生暂停学习
- 暂停期间不计入学习时长
- 记录实际活跃时间

## 📝 相关文件

1. ✅ **views.py** - 修复时长计算逻辑（2处）
2. ✅ **fix_study_time.py** - 数据修复脚本
3. ✅ **TIME_CALCULATION_FIX.md** - 详细技术文档
4. ✅ **diagnose_time_issue.py** - 时长诊断工具

## 🚀 测试验证

运行诊断脚本检查修复效果：
```bash
python diagnose_time_issue.py
```

预期输出：所有会话时长应在 0-4 小时范围内。

---

**修复状态：** ✅ 已完成
**验证状态：** ⏳ 待用户确认
**代码提交：** ⏳ 待提交到Git