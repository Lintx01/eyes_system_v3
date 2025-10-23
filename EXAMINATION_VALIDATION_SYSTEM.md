# 检查选择严格验证系统

## 功能概述

本系统实现了严格的检查选择验证机制，确保学生必须完全正确选择教师设定的所有必选检查项目后，方可进入下一步骤。系统会对错误选择进行记录并应用评分惩罚。

## 核心特性

### 🎯 严格验证机制
- **完全匹配要求**: 学生选择必须与教师设置的必选项目完全一致
- **不能多选**: 选择多余的检查项目将被视为错误
- **不能少选**: 遗漏任何必选检查项目将被视为错误
- **阻断式验证**: 只有完全正确选择后才能继续流程

### 📊 智能评分惩罚
- **递进式惩罚**: 错误次数越多，惩罚越重
  - 第1次错误: 扣5分 + 严重度惩罚
  - 第2次错误: 扣10分 + 严重度惩罚
  - 第3次错误: 扣15分 + 严重度惩罚
  - 第4次及以上: 扣20分 + 严重度惩罚

- **严重度评估**:
  - 缺少必选项: 每项扣3分
  - 多选项目: 每项扣2分
  - 单次最大惩罚: 30分

### 🎨 用户体验优化
- **详细错误提示**: 明确指出缺少的必选项和多选的项目
- **视觉高亮**: 错误项目会有颜色标识和动画效果
- **递进式引导**: 根据尝试次数提供不同程度的提示
- **实时反馈**: 立即显示错误详情和惩罚信息

## 技术实现

### 后端验证函数

#### 1. `validate_examination_selection()`
验证学生选择是否符合要求的核心函数：
```python
def validate_examination_selection(required_exam_ids, selected_exam_ids, required_exams, session):
    """
    严格验证检查选择
    - required_exam_ids: 必选检查项目ID集合
    - selected_exam_ids: 学生选择的检查项目ID集合
    - required_exams: 必选检查项目QuerySet
    - session: 学生会话对象
    """
```

#### 2. `calculate_examination_penalty()`
计算错误选择的惩罚分数：
```python
def calculate_examination_penalty(attempt_count, missing_count, extra_count):
    """
    计算惩罚分数
    - attempt_count: 错误尝试次数
    - missing_count: 缺少的必选项数量
    - extra_count: 多选的项目数量
    """
```

#### 3. `record_examination_error()`
记录错误操作和应用惩罚：
```python
def record_examination_error(session, validation_result):
    """
    记录错误详情并更新会话状态
    - session: StudentClinicalSession实例
    - validation_result: 验证结果字典
    """
```

### 前端交互逻辑

#### 1. 错误显示函数
```javascript
function showExaminationValidationError(errorResponse) {
    // 显示详细的验证错误信息
    // 包含缺少项目、多选项目、惩罚信息等
}
```

#### 2. 错误高亮系统
```javascript
function highlightErrorExaminations(errorDetails) {
    // 高亮显示错误的检查项目
    // 红色标识缺少的必选项
    // 黄色标识多选的项目
}
```

#### 3. 状态清理函数
```javascript
function clearExaminationErrors() {
    // 清除错误状态和高亮效果
    // 重置反馈面板内容
}
```

## 数据记录结构

### 错误记录格式
每次错误都会记录在`session.session_data['examination_selection_errors']`中：
```json
{
    "timestamp": "2024-10-23T10:30:00",
    "attempt_number": 1,
    "missing_required_count": 2,
    "extra_selected_count": 1,
    "missing_required_ids": [1, 3],
    "extra_selected_ids": [5],
    "penalty_applied": 11,
    "error_message": "选择有误，请检查后重新选择..."
}
```

### 成功记录格式
成功完成后记录在`session.session_data['examination_selection_success']`中：
```json
{
    "timestamp": "2024-10-23T10:35:00",
    "final_attempt": 2,
    "total_errors": 1,
    "total_penalty": 11
}
```

## 评分影响

### 基础评分计算
```python
# 基础得分 = (必选检查70% + 检查效率30%) * 100
base_score = (required_score * 0.7 + efficiency_score * 0.3) * 100

# 最终得分 = 基础得分 - 选择错误惩罚
final_score = max(0, base_score - selection_penalty)
```

### 惩罚累积
- 每次错误选择都会累积惩罚分数
- 惩罚分数从最终检查选择得分中扣除
- 最低得分不会低于0分

## 教学价值

### 1. 强化临床思维
- 迫使学生仔细分析病例需求
- 避免盲目选择或投机取巧
- 培养严谨的临床决策能力

### 2. 真实临床模拟
- 模拟临床实际中的精准诊断要求
- 强调检查选择的重要性和后果
- 培养成本效益意识

### 3. 学习行为引导
- 鼓励深入理解而非表面记忆
- 通过惩罚机制引导正确学习行为
- 提供明确的对错反馈

## 使用流程

### 教师端操作
1. 在检查选项管理页面设置必选检查项目
2. 使用"批量设置必选项"功能快速配置
3. 系统自动启用严格验证模式

### 学生端体验
1. 进入检查选择阶段
2. 从混合后的检查选项中进行选择
3. 点击"确认检查选择"进行提交
4. 系统验证选择是否完全正确:
   - ✅ 正确: 继续下一步骤
   - ❌ 错误: 显示详细错误信息和惩罚
5. 根据错误提示调整选择后重新提交

### 错误处理流程
1. 系统检测到选择错误
2. 记录错误详情和应用惩罚
3. 显示具体的错误信息:
   - 缺少哪些必选检查项
   - 多选了哪些不必要的项目
   - 本次扣除的分数
   - 操作建议
4. 高亮显示错误项目
5. 学生调整选择后重新尝试

## 配置建议

### 必选项设置原则
- **数量适中**: 建议2-6个必选项
- **核心关键**: 选择对诊断最重要的检查
- **难度递进**: 根据案例复杂度调整必选项数量
- **类型平衡**: 涵盖不同类型的检查方法

### 惩罚机制调整
当前惩罚参数可在`calculate_examination_penalty()`函数中调整：
- 基础惩罚强度
- 严重度权重
- 最大惩罚限制

## 监控和分析

系统提供以下数据用于教学效果评估：
- 学生错误尝试次数分布
- 常见错误类型分析
- 惩罚分数对学习行为的影响
- 不同案例的验证通过率

## 技术特点

1. **双重验证**: 前后端协同验证，确保数据安全
2. **状态持久化**: 错误记录永久保存，便于追踪分析
3. **用户体验**: 丰富的视觉反馈和引导提示
4. **性能优化**: 高效的数据库查询和前端渲染
5. **扩展性**: 便于后续功能扩展和参数调整

## 注意事项

1. **向后兼容**: 未设置必选项的案例仍使用标准模式
2. **数据完整性**: 确保检查选项数据的准确性
3. **用户体验**: 避免过度惩罚影响学习积极性
4. **性能考虑**: 大量并发验证时的响应速度
5. **错误恢复**: 提供重置和回退机制

通过这套严格验证系统，学生将获得更真实、更有挑战性的临床推理训练体验，同时教师可以更精确地评估学生的临床思维能力。