"""
诊断推理相关API视图
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import get_object_or_404
from .models import ClinicalCase, DiagnosisOption, StudentClinicalSession
import json
import re
from difflib import SequenceMatcher


def is_student(user):
    """检查用户是否为学生"""
    # 简单起见，只要是认证用户且不是staff就视为学生
    return user.is_authenticated and not user.is_staff


@login_required
@user_passes_test(is_student, login_url='login')
def get_diagnosis_options(request, case_id):
    """
    获取诊断选项列表
    返回：当前病例的正确诊断 + 其他病例的正确诊断作为干扰项
    """
    try:
        import random
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 1. 获取当前病例的正确诊断选项（支持多正确诊断）
        correct_diagnoses = list(
            DiagnosisOption.objects.filter(clinical_case=clinical_case, is_correct_diagnosis=True)
        )

        # 配置校验：避免用 4xx 触发前端“网络错误/请刷新”提示
        if not correct_diagnoses:
            has_any_options = DiagnosisOption.objects.filter(clinical_case=clinical_case).exists()
            if not has_any_options:
                msg = '该病例尚未配置诊断选项，请联系教师在教师端添加诊断选项'
            else:
                msg = '该病例未设置“正确诊断”，请教师在诊断选项中勾选至少一个“这是正确诊断”'
            return JsonResponse({'success': False, 'message': msg}, status=200)
        
        # 2. 从其他病例中随机选择正确诊断作为干扰项（排除当前病例）
        # 目标：默认总选项数约为5（1个正确+4个干扰）
        target_total = 5
        distractor_count = max(0, target_total - len(correct_diagnoses))
        correct_names = {d.diagnosis_name for d in correct_diagnoses}
        distractor_diagnoses = list(DiagnosisOption.objects.filter(
            is_correct_diagnosis=True
        ).exclude(
            clinical_case=clinical_case
        ).exclude(
            diagnosis_name__in=correct_names  # 排除同名诊断
        ))
        
        # 随机选择干扰项
        if distractor_count > 0 and len(distractor_diagnoses) > distractor_count:
            selected_distractors = random.sample(distractor_diagnoses, distractor_count)
        else:
            selected_distractors = distractor_diagnoses[:distractor_count] if distractor_count > 0 else []
        
        # 3. 合并选项并随机排序
        all_options = correct_diagnoses + selected_distractors
        random.shuffle(all_options)
        
        # 4. 构建返回数据（不返回is_correct字段给前端）
        options_data = [{
            'id': option.id,
            'name': option.diagnosis_name,
            'description': option.diagnosis_description or '',
            'difficulty': option.difficulty_level,
        } for option in all_options]
        
        return JsonResponse({
            'success': True,
            'data': {
                'diagnosis_options': options_data,
                'total_count': len(options_data),
                # 不泄露正确答案，只告知是否允许多选
                'allow_multiple': len(correct_diagnoses) > 1
            },
            'message': '诊断选项获取成功'
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'message': f'获取诊断选项失败：{str(e)}',
            'traceback': traceback.format_exc()
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
@require_POST
def submit_diagnosis(request, case_id):
    """提交诊断并评分（支持单选和多选）"""
    try:
        # 解析请求数据
        data = json.loads(request.body)
        
        # 支持单选和多选两种格式
        # 单选: diagnosis_id (单个ID)
        # 多选: diagnosis_ids (ID列表)
        diagnosis_ids = data.get('diagnosis_ids') or [data.get('diagnosis_id')]
        diagnosis_ids = [id for id in diagnosis_ids if id]  # 过滤None值
        
        diagnosis_rationale = data.get('diagnosis_rationale', '').strip()
        
        # 验证数据
        if not diagnosis_ids or not diagnosis_rationale:
            return JsonResponse({
                'success': False,
                'message': '请选择诊断并填写诊断依据'
            }, status=400)
        
        # 获取病例
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 获取所有提交的诊断选项
        diagnosis_options = DiagnosisOption.objects.filter(id__in=diagnosis_ids)
        
        # 获取或创建学生会话
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={
                'session_status': 'diagnosis',
                'session_data': {}
            }
        )
        
        # 评分逻辑
        
        # 获取当前病例的所有正确诊断
        correct_diagnoses = DiagnosisOption.objects.filter(
            clinical_case=clinical_case,
            is_correct_diagnosis=True
        )
        correct_diagnosis_ids = set(correct_diagnoses.values_list('id', flat=True))
        selected_diagnosis_ids = set(diagnosis_ids)
        
        # 1. 诊断选择评分（0-100分）
        # 计算准确率和召回率
        if len(correct_diagnosis_ids) == 0:
            return JsonResponse({
                'success': False,
                'message': '该病例没有设置正确诊断，请联系教师'
            }, status=400)
        
        # 正确选中的数量
        correctly_selected = len(selected_diagnosis_ids & correct_diagnosis_ids)
        # 错误选中的数量（选了不该选的）
        incorrectly_selected = len(selected_diagnosis_ids - correct_diagnosis_ids)
        # 遗漏的数量（没选应该选的）
        missed = len(correct_diagnosis_ids - selected_diagnosis_ids)
        
        # 评分规则：
        # - 全部选对且没有多选：100分
        # - 部分正确：按比例给分，但要扣除错选的分数
        if missed == 0 and incorrectly_selected == 0:
            diagnosis_score = 100  # 完全正确
            is_correct = True
        else:
            # 准确率：选中的正确诊断 / 总共选中的诊断
            precision = correctly_selected / len(selected_diagnosis_ids) if selected_diagnosis_ids else 0
            # 召回率：选中的正确诊断 / 应该选中的诊断
            recall = correctly_selected / len(correct_diagnosis_ids)
            # F1分数作为诊断分数
            if precision + recall > 0:
                f1_score = 2 * (precision * recall) / (precision + recall)
                diagnosis_score = f1_score * 100
            else:
                diagnosis_score = 0
            is_correct = False
        
        # 2. 诊断依据评分（0-100分）- 使用第一个正确诊断的标准答案
        first_correct = correct_diagnoses.first()
        rationale_score = calculate_rationale_score(
            diagnosis_rationale, 
            first_correct.correct_rationale if first_correct.correct_rationale else "",
            first_correct.key_points if first_correct.key_points else ""
        )
        
        # 3. 总分计算（诊断占70%，依据占30%）
        total_score = diagnosis_score * 0.7 + rationale_score * 0.3
        
        # 生成反馈
        selected_names = [opt.diagnosis_name for opt in diagnosis_options]
        correct_names = [d.diagnosis_name for d in correct_diagnoses]
        
        feedback_parts = []
        if is_correct:
            feedback_parts.append(f"✓ 诊断完全正确！您选择了所有正确的诊断。")
        else:
            if correctly_selected > 0:
                feedback_parts.append(f"部分正确：您选中了 {correctly_selected}/{len(correct_diagnosis_ids)} 个正确诊断。")
            if incorrectly_selected > 0:
                wrong_names = list(selected_diagnosis_ids - correct_diagnosis_ids)
                feedback_parts.append(f"❌ 错误选择了 {incorrectly_selected} 个不正确的诊断。")
            if missed > 0:
                feedback_parts.append(f"⚠️ 遗漏了 {missed} 个应该选择的诊断。")
            feedback_parts.append(f"\n正确答案：{', '.join(correct_names)}")
        
        feedback = "\n".join(feedback_parts)
        
        # 保存到会话数据
        if not session.session_data:
            session.session_data = {}
        
        session.session_data['diagnosis'] = {
            'diagnosis_ids': diagnosis_ids,
            'diagnosis_names': selected_names,
            'diagnosis_rationale': diagnosis_rationale,
            'is_correct': is_correct,
            'correctly_selected': correctly_selected,
            'incorrectly_selected': incorrectly_selected,
            'missed': missed,
            'diagnosis_score': round(diagnosis_score, 2),
            'rationale_score': round(rationale_score, 2),
            'total_score': round(total_score, 2)
        }
        
        # 如果诊断完全正确，进入治疗阶段；否则保持在诊断阶段允许重试
        if is_correct:
            session.session_status = 'treatment_selection'
            session.diagnosis_score = round(total_score, 2)
        else:
            session.session_status = 'diagnosis_reasoning'
        
        session.save()
        
        return JsonResponse({
            'success': True,
            'data': {
                'is_correct': is_correct,
                'diagnosis_score': round(diagnosis_score, 2),
                'rationale_score': round(rationale_score, 2),
                'total_score': round(total_score, 2),
                'feedback': feedback,
                'correctly_selected': correctly_selected,
                'incorrectly_selected': incorrectly_selected,
                'missed': missed,
                'correct_diagnoses': correct_names if not is_correct else None
            },
            'message': '诊断提交成功'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'诊断提交失败：{str(e)}'
        }, status=500)


def calculate_rationale_score(student_rationale, correct_rationale, key_points):
    """
    计算诊断依据得分
    基于：
    1. 与标准答案的文本相似度
    2. 关键点覆盖率
    """
    if not correct_rationale and not key_points:
        # 如果没有标准答案，按字数给基础分
        word_count = len(student_rationale)
        if word_count >= 200:
            return 80
        elif word_count >= 100:
            return 60
        elif word_count >= 50:
            return 40
        else:
            return 20
    
    score = 0
    
    # 1. 文本相似度得分（60分）
    if correct_rationale:
        similarity = SequenceMatcher(None, student_rationale, correct_rationale).ratio()
        score += similarity * 60
    
    # 2. 关键点覆盖率（40分）
    if key_points:
        if isinstance(key_points, str):
            # 如果是字符串，尝试按逗号或分号分割
            key_points = [kp.strip() for kp in re.split('[,，;；]', key_points) if kp.strip()]
        
        matched_points = 0
        for point in key_points:
            if point.lower() in student_rationale.lower():
                matched_points += 1
        
        if len(key_points) > 0:
            coverage_rate = matched_points / len(key_points)
            score += coverage_rate * 40
    
    # 字数奖励（最多10分）
    word_count = len(student_rationale)
    if word_count >= 200:
        score += 10
    elif word_count >= 100:
        score += 5
    
    return min(score, 100)


def generate_diagnosis_feedback(is_correct, rationale_score, diagnosis_name, correct_rationale):
    """生成诊断反馈"""
    feedback = []
    
    if is_correct:
        feedback.append("✓ 诊断正确！")
    else:
        feedback.append(f"✗ 诊断不正确。您选择的是：{diagnosis_name}")
    
    if rationale_score >= 80:
        feedback.append("✓ 诊断依据充分完整，分析清晰。")
    elif rationale_score >= 60:
        feedback.append("○ 诊断依据基本合理，但可以更加详细和全面。")
    else:
        feedback.append("✗ 诊断依据不够充分，请结合病史、检查结果进行更全面的分析。")
    
    if correct_rationale and rationale_score < 80:
        feedback.append(f"\n参考答案：\n{correct_rationale}")
    
    return '\n'.join(feedback)
