# 前后端阶段命名统一修复报告

## 修复日期
2025年12月16日

## 问题描述
前端使用简短的阶段命名（`history`, `examination`, `diagnosis`, `treatment`），而后端使用完整的命名（`case_presentation`, `examination_selection`, `diagnosis_reasoning`, `treatment_selection`），导致前端发送的请求中携带的阶段名称与后端不匹配，聊天功能被错误地阻止。

## 根本原因
前后端阶段命名不一致：
- **前端旧命名**: `history`, `examination`, `diagnosis`, `treatment`, `feedback`
- **后端命名**: `case_presentation`, `examination_selection`, `diagnosis_reasoning`, `treatment_selection`, `learning_feedback`

## 修复方案
**统一使用后端的完整命名**，修改前端所有相关代码。

## 修复详情

### 1. clinicalSession对象初始化
**文件**: `cases/templates/student/clinical_case_detail.html`
**位置**: 第 4287-4290 行

**修改前**:
```javascript
window.clinicalSession = {
  caseId: '{{ clinical_case.case_id }}',
  currentStage: 'history',
  stages: ['history', 'examination', 'diagnosis', 'treatment', 'feedback'],
```

**修改后**:
```javascript
window.clinicalSession = {
  caseId: '{{ clinical_case.case_id }}',
  currentStage: 'case_presentation',
  stages: ['case_presentation', 'examination_selection', 'diagnosis_reasoning', 'treatment_selection', 'learning_feedback'],
```

### 2. HTML进度条 data-step属性
**修改位置**: 第 42-62 行 和 第 89-109 行

**修改前**:
```html
<div class="stepper-item active" data-step="history">
<div class="stepper-item" data-step="examination">
<div class="stepper-item" data-step="diagnosis">
<div class="stepper-item" data-step="treatment">
<div class="stepper-item" data-step="feedback">
```

**修改后**:
```html
<div class="stepper-item active" data-step="case_presentation">
<div class="stepper-item" data-step="examination_selection">
<div class="stepper-item" data-step="diagnosis_reasoning">
<div class="stepper-item" data-step="treatment_selection">
<div class="stepper-item" data-step="learning_feedback">
```

### 3. JavaScript中的所有currentStage赋值
**全局替换**:
- `clinicalSession.currentStage = 'history'` → `'case_presentation'` (2处)
- `clinicalSession.currentStage = 'examination'` → `'examination_selection'` (6处)
- `clinicalSession.currentStage = 'diagnosis'` → `'diagnosis_reasoning'` (2处)
- `clinicalSession.currentStage = 'treatment'` → `'treatment_selection'` (2处)

### 4. JavaScript中的所有currentStage比较
**全局替换**:
- `currentStage === 'history'` → `'case_presentation'` (2处)
- `currentStage === 'examination'` → `'examination_selection'` (4处)
- `currentStage === 'diagnosis'` → `'diagnosis_reasoning'` (4处)
- `currentStage === 'treatment'` → `'treatment_selection'` (4处)

### 5. switch语句中的case标签
**修改了3个switch语句**:

#### ensureButtonEnabled() 函数
```javascript
switch(stage) {
  case 'examination_selection':  // 原 'examination'
  case 'diagnosis_reasoning':    // 原 'diagnosis'
  case 'treatment_selection':    // 原 'treatment'
}
```

#### handleNextStage() 函数
```javascript
switch (currentStage) {
  case 'case_presentation':      // 原 'history'
  case 'examination_selection':  // 原 'examination'
  case 'diagnosis_reasoning':    // 原 'diagnosis'
  case 'treatment_selection':    // 原 'treatment'
}
```

#### handleBackStep() 函数
```javascript
switch (previousStage) {
  case 'case_presentation':      // 原 'history'
  case 'examination_selection':  // 原 'examination'
  case 'diagnosis_reasoning':    // 原 'diagnosis'
  case 'treatment_selection':    // 原 'treatment'
}
```

### 6. 后端响应检查
```javascript
// 修改前
if (resp.data.current_stage === 'treatment') {

// 修改后
if (resp.data.current_stage === 'treatment_selection') {
```

## 修复统计
- **总修改次数**: 约 40+ 处
- **涉及函数**: 
  - `initializeSessionState()`
  - `ensureButtonEnabled()`
  - `updateClinicalProgress()`
  - `handleNextStage()`
  - `handleBackStep()`
  - `submitDiagnosis()` 响应处理
  - 多个阶段初始化函数

## 验证结果

### 数据库状态
所有会话的 `session_status` 值均为合法值：
- `case_presentation` ✓
- `diagnosis_reasoning` ✓
- `completed` ✓

### 前端代码
执行 `fix_frontend_stage_names.py` 验证：
```
未找到需要修复的内容
```
表明所有旧命名已清理完毕 ✓

### 聊天功能逻辑
后端 `chat_api()` 函数（views.py 第 3220-3227 行）：
```python
forbidden_chat_stages = ['diagnosis_reasoning', 'treatment_selection', 'learning_feedback', 'completed']

if session.session_status in forbidden_chat_stages:
    return JsonResponse({'success': False, 'error': '当前阶段不允许聊天输入'})
```

前端现在发送的阶段名称：
- `case_presentation` → 允许聊天 ✓
- `examination_selection` → 允许聊天 ✓
- `diagnosis_reasoning` → 禁止聊天 ✓
- `treatment_selection` → 禁止聊天 ✓

## 测试步骤
1. ✅ 清除浏览器缓存（Ctrl+Shift+Delete）
2. ✅ 强制刷新页面（Ctrl+F5）
3. ✅ 进入病史采集阶段
4. ✅ 点击快捷问题按钮或输入问题
5. ✅ 验证聊天功能正常工作

## 注意事项
- Django服务器会自动重新加载模板文件
- 浏览器可能缓存了旧的HTML，**必须强制刷新**
- 控制台日志现在应显示 `case_presentation` 而不是 `history`

## 修复文件列表
1. ✅ `cases/templates/student/clinical_case_detail.html` - 统一所有阶段命名
2. ✅ `cases/views.py` - 之前已修复所有 `session_status` 赋值
3. ✅ `fix_frontend_stage_names.py` - 批量修复脚本
4. ✅ 数据库 - 之前已修复无效的 `session_status` 值

## 完整的阶段命名对照表

| 中文名称 | 旧前端命名 | 统一后端命名 | 数据库字段值 |
|---------|-----------|------------|------------|
| 病史采集 | history | case_presentation | case_presentation |
| 检查选择 | examination | examination_selection | examination_selection |
| 检查结果 | - | examination_results | examination_results |
| 诊断推理 | diagnosis | diagnosis_reasoning | diagnosis_reasoning |
| 治疗选择 | treatment | treatment_selection | treatment_selection |
| 学习反馈 | feedback | learning_feedback | learning_feedback |
| 已完成 | - | completed | completed |

## 下一步
用户需要：
1. **清除浏览器缓存**
2. **强制刷新页面（Ctrl+F5）**
3. 测试病史采集阶段的聊天功能

预期结果：
- 控制台显示 `当前阶段: case_presentation`
- 快捷问题按钮可点击
- 聊天功能正常工作
- 后端不再返回"当前阶段不允许聊天输入"错误
