# AJAX交互功能实现指南

## 概述

我们为眼科教学系统添加了完整的AJAX交互功能，包括：
1. 实时获取用户学习进度
2. 异步提交练习答案
3. 题目答题统计分析
4. 考试状态实时监控

## 🚀 新增的后端API接口

### 1. 用户进度接口
- **URL**: `GET /api/user/progress/`
- **功能**: 获取当前用户的学习进度统计
- **返回数据**:
```json
{
  "success": true,
  "data": {
    "progress_percentage": 65.5,
    "total_cases": 20,
    "completed_cases": 13,
    "total_exercises": 150,
    "completed_exercises": 98,
    "total_study_time": 1200,
    "last_study_date": "2025-10-11 15:30:00",
    "recent_answers": [...]
  }
}
```

### 2. 保存练习答案接口
- **URL**: `POST /api/exercise/save-answer/`
- **参数**: `exercise_id`, `answer`
- **功能**: 异步提交练习答案并返回结果
- **返回数据**:
```json
{
  "success": true,
  "data": {
    "is_correct": true,
    "correct_answer": "A",
    "explanation": "详细解析...",
    "user_answer": "A",
    "progress_percentage": 66.0
  }
}
```

### 3. 题目统计接口
- **URL**: `GET /api/exercise/{id}/statistics/`
- **功能**: 获取指定题目的答题统计信息
- **返回数据**:
```json
{
  "success": true,
  "data": {
    "exercise_id": 1,
    "question": "题目内容...",
    "total_answers": 85,
    "correct_answers": 68,
    "accuracy": 80.0,
    "correct_answer": "A",
    "answer_stats": {
      "A": {"option": "选项A内容", "count": 68, "percentage": 80.0},
      "B": {"option": "选项B内容", "count": 12, "percentage": 14.1},
      "C": {"option": "选项C内容", "count": 3, "percentage": 3.5},
      "D": {"option": "选项D内容", "count": 2, "percentage": 2.4}
    }
  }
}
```

### 4. 考试状态接口
- **URL**: `GET /api/exam/{id}/status/`
- **功能**: 获取考试实时状态和剩余时间
- **返回数据**:
```json
{
  "success": true,
  "data": {
    "exam_id": 1,
    "status": "in_progress",
    "status_text": "进行中",
    "time_left": 3600,
    "formatted_time": "01:00:00",
    "total_participants": 25,
    "current_participants": 18,
    "can_start": true,
    "is_finished": false
  }
}
```

## 🎨 前端实现要点

### 1. CSRF保护
所有POST请求必须包含CSRF token：
```javascript
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}
const csrftoken = getCookie('csrftoken');

// 在请求中使用
fetch('/api/exercise/save-answer/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken
    },
    body: formData,
    credentials: 'same-origin'
})
```

### 2. 错误处理
```javascript
.then(response => response.json())
.then(data => {
    if (!data.success) {
        alert(data.error || '操作失败');
        return;
    }
    // 处理成功情况
})
.catch(error => {
    console.error('网络错误:', error);
    alert('网络错误，请稍后重试');
});
```

### 3. 实时更新示例
```javascript
// 每3秒轮询考试状态
function pollExamStatus(examId) {
    fetch(`/api/exam/${examId}/status/`)
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateTimer(data.data.formatted_time);
            if (data.data.status === 'finished') {
                submitExam(); // 自动提交
            }
        }
    });
}
setInterval(() => pollExamStatus(examId), 3000);
```

## 🎯 已实现的功能

### 教师端统计功能
- ✅ 在`teacher/exercise_list.html`中添加了"查看统计"按钮
- ✅ 实现了统计数据弹窗显示
- ✅ 显示总答题数、正确率、各选项分布等信息
- ✅ 支持数据刷新功能

### 学生端可扩展功能
1. **异步答题**: 可将`student/exercise.html`的表单提交改为AJAX
2. **进度实时更新**: 答题后即时更新学习进度
3. **考试倒计时**: 实时显示剩余时间并自动提交

## 🔧 如何测试

### 1. 启动开发服务器
```powershell
cd g:\AAA_眼科教学软件\eyes_system\eyessystem\system
python manage.py runserver 8000
```

### 2. 使用测试页面
打开 `g:\AAA_眼科教学软件\eyes_system\ajax_test.html` 来测试各个API接口

### 3. 在浏览器中测试
1. 访问教师端练习列表：`http://127.0.0.1:8000/teacher/cases/1/exercises/`
2. 点击任意题目的"统计"按钮
3. 查看弹窗中的统计信息

### 4. 开发者工具调试
- 打开浏览器开发者工具（F12）
- 查看Network标签页观察AJAX请求
- 查看Console标签页观察错误信息

## 📝 使用示例

### 在模板中添加AJAX调用
```html
<script>
function loadStats(exerciseId) {
    fetch(`/api/exercise/${exerciseId}/statistics/`)
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            document.getElementById('accuracy').textContent = data.data.accuracy + '%';
            document.getElementById('total').textContent = data.data.total_answers;
        }
    })
    .catch(e => console.error(e));
}
</script>
```

### 实现实时进度更新
```javascript
function updateProgress() {
    fetch('/api/user/progress/')
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const p = data.data.progress_percentage;
            document.querySelector('.progress-bar').style.width = p + '%';
        }
    });
}
```

## 🚦 注意事项

1. **认证要求**: 所有接口都需要用户登录
2. **权限控制**: 部分接口有角色限制（学生/教师）
3. **CSRF保护**: POST请求必须包含有效的CSRF token
4. **错误处理**: 始终检查返回的`success`字段
5. **性能考虑**: 避免过于频繁的轮询请求

## 🔄 扩展方向

1. **WebSocket支持**: 实现真正的实时通信
2. **离线缓存**: 支持离线答题和后续同步
3. **进度动画**: 添加更丰富的UI动画效果
4. **数据可视化**: 使用图表库展示统计数据
5. **移动端优化**: 适配移动设备的触摸交互

---

这份指南涵盖了AJAX功能的完整实现，可以帮助你进一步开发和维护系统。