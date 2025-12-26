"""
治疗方案阶段的视图函数
包括：获取治疗选项、提交治疗方案、评分等功能
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from cases.models import ClinicalCase, TreatmentOption, StudentClinicalSession
import json
from difflib import SequenceMatcher


def is_student(user):
    """检查用户是否是学生"""
    return not user.is_staff


@login_required
@user_passes_test(is_student, login_url='login')
def get_treatment_options(request, case_id):
    """
    获取治疗选项列表
    返回：当前病例的最佳治疗 + 其他病例的最佳治疗作为干扰项
    """
    try:
        import random
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 1. 获取当前病例的最佳治疗选项
        optimal_treatments = list(TreatmentOption.objects.filter(
            clinical_case=clinical_case,
            is_optimal=True
        ))
        
        if not optimal_treatments:
            return JsonResponse({
                'success': False,
                'message': '该病例没有设置最佳治疗方案，请联系教师'
            }, status=400)
        
        # 2. 从其他病例中随机选择最佳治疗作为干扰项（排除当前病例）
        distractor_count = 3  # 干扰项数量
        distractor_treatments = list(TreatmentOption.objects.filter(
            is_optimal=True
        ).exclude(
            clinical_case=clinical_case
        ))
        
        # 排除同名治疗
        optimal_names = {t.treatment_name for t in optimal_treatments}
        distractor_treatments = [t for t in distractor_treatments if t.treatment_name not in optimal_names]
        
        # 随机选择干扰项
        if len(distractor_treatments) > distractor_count:
            selected_distractors = random.sample(distractor_treatments, distractor_count)
        else:
            selected_distractors = distractor_treatments
        
        # 3. 合并选项并随机排序
        all_options = optimal_treatments + selected_distractors
        random.shuffle(all_options)
        
        # 4. 构建返回数据（包含所有必要字段用于前端显示）
        options_data = [{
            'id': option.id,
            'name': option.treatment_name,
            'description': option.treatment_description or '',
            'type': option.treatment_type,
            'difficulty': option.difficulty_level,
            'is_acceptable': option.is_acceptable,
            'is_contraindicated': option.is_contraindicated,
            'efficacy_score': option.efficacy_score,
            'safety_score': option.safety_score,
            'cost_score': option.cost_score,
            'expected_outcome': option.expected_outcome or ''
        } for option in all_options]
        
        return JsonResponse({
            'success': True,
            'data': {
                'treatment_options': options_data,
                'total_count': len(options_data),
                'optimal_count': len(optimal_treatments)
            },
            'message': '治疗选项获取成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取治疗选项失败: {str(e)}'
        }, status=500)


@require_POST
@login_required
@user_passes_test(is_student, login_url='login')
def submit_treatment(request, case_id):
    """提交治疗方案并评分"""
    try:
        # 解析请求数据
        data = json.loads(request.body)
        treatment_ids = data.get('treatment_ids', [])  # 支持多选
        treatment_rationale = data.get('treatment_rationale', '').strip()
        
        # 兼容单选格式
        if not treatment_ids and data.get('treatment_id'):
            treatment_ids = [data.get('treatment_id')]
        
        # 验证数据
        if not treatment_ids or not treatment_rationale:
            return JsonResponse({
                'success': False,
                'message': '请选择治疗方案并填写治疗依据'
            }, status=400)
        
        # 获取病例
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 获取所有选中的治疗选项
        selected_treatments = TreatmentOption.objects.filter(id__in=treatment_ids)
        
        if selected_treatments.count() != len(treatment_ids):
            return JsonResponse({
                'success': False,
                'message': '部分治疗选项不存在'
            }, status=400)
        
        # 获取或创建学生会话
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={
                'session_status': 'treatment_selection',
                'session_data': {}
            }
        )
        
        # 评分逻辑
        
        # 1. 获取当前病例的所有最佳治疗
        optimal_treatments = set(TreatmentOption.objects.filter(
            clinical_case=clinical_case,
            is_optimal=True
        ).values_list('id', flat=True))
        
        # 2. 计算治疗选择评分
        selected_ids = set(treatment_ids)
        
        # 正确选择的治疗（在最佳治疗列表中）
        correct_selections = selected_ids & optimal_treatments
        # 错误选择的治疗（不在最佳治疗列表中）
        incorrect_selections = selected_ids - optimal_treatments
        # 遗漏的治疗（在最佳治疗中但未选）
        missed_selections = optimal_treatments - selected_ids
        
        # 治疗选择得分计算
        if len(optimal_treatments) == 0:
            treatment_score = 0
        else:
            # 基础分：正确率
            correct_rate = len(correct_selections) / len(optimal_treatments)
            # 扣分：错误选择和遗漏
            penalty = (len(incorrect_selections) + len(missed_selections)) * 0.1
            treatment_score = max(0, (correct_rate - penalty)) * 100
        
        # 3. 治疗依据评分（基于文本相似度）
        # 使用第一个正确选择的治疗的依据作为参考
        if correct_selections:
            reference_treatment = TreatmentOption.objects.filter(
                id__in=correct_selections
            ).first()
            rationale_score = calculate_rationale_score(
                treatment_rationale,
                reference_treatment.correct_rationale,
                reference_treatment.key_points
            )
        else:
            # 如果没有正确选择，依据得分为0
            rationale_score = 0
        
        # 4. 总分计算（治疗选择占70%，依据占30%）
        total_score = treatment_score * 0.7 + rationale_score * 0.3
        
        # 5. 判断是否完全正确
        is_perfect = (
            len(correct_selections) == len(optimal_treatments) and
            len(incorrect_selections) == 0
        )
        
        # 6. 生成反馈
        feedback = generate_treatment_feedback(
            is_perfect,
            len(correct_selections),
            len(optimal_treatments),
            len(incorrect_selections),
            rationale_score,
            selected_treatments
        )
        
        # 7. 保存到会话数据
        if not session.session_data:
            session.session_data = {}
        
        session.session_data['treatment'] = {
            'treatment_ids': treatment_ids,
            'treatment_names': [t.treatment_name for t in selected_treatments],
            'treatment_rationale': treatment_rationale,
            'is_perfect': is_perfect,
            'correct_count': len(correct_selections),
            'incorrect_count': len(incorrect_selections),
            'missed_count': len(missed_selections),
            'treatment_score': round(treatment_score, 2),
            'rationale_score': round(rationale_score, 2),
            'total_score': round(total_score, 2)
        }
        
        # 更新会话状态与评分（用于总体得分计算与统计口径）
        session.selected_treatments = list(treatment_ids)
        session.treatment_score = round(total_score, 2)

        if is_perfect:
            now = timezone.now()
            now_iso = now.isoformat()
            old_stage = getattr(session, 'session_status', None)

            # 通过后端统一计算总体得分，避免前端出现“总分=0”的默认值问题
            session.calculate_overall_score()
            session.completed_at = now
            session.session_status = 'learning_feedback'

            # 同步更新 last_activity / stage_start_times / stage_times，避免“完成时间早于学习反馈开始时间”
            try:
                if hasattr(session, 'last_activity'):
                    session.last_activity = now
            except Exception:
                pass

            try:
                if not session.session_data:
                    session.session_data = {}
                if not session.session_data.get('run_started_at'):
                    session.session_data['run_started_at'] = now_iso

                stage_start_times = session.session_data.get('stage_start_times')
                if not isinstance(stage_start_times, dict):
                    stage_start_times = {}
                if not stage_start_times.get('learning_feedback'):
                    stage_start_times['learning_feedback'] = now_iso
                session.session_data['stage_start_times'] = stage_start_times

                if old_stage and old_stage != 'learning_feedback':
                    stage_times = session.session_data.get('stage_times')
                    if not isinstance(stage_times, dict):
                        stage_times = {}
                    stage_times[f'{old_stage}_to_learning_feedback'] = now_iso
                    session.session_data['stage_times'] = stage_times
            except Exception:
                pass
        session.save()

        overall_feedback = None
        if is_perfect:
            overall_feedback = f"恭喜完成临床推理！总体得分：{session.overall_score:.1f}分。"
            if session.overall_score >= 90:
                overall_feedback += "表现优秀！您展现了出色的临床思维能力。"
            elif session.overall_score >= 70:
                overall_feedback += "表现良好，继续努力提升临床推理能力。"
            else:
                overall_feedback += "还有提升空间，建议复习相关知识点。"
        
        return JsonResponse({
            'success': True,
            'data': {
                'is_perfect': is_perfect,
                'correct_count': len(correct_selections),
                'total_optimal': len(optimal_treatments),
                'incorrect_count': len(incorrect_selections),
                'treatment_score': round(treatment_score, 2),
                'rationale_score': round(rationale_score, 2),
                'total_score': round(total_score, 2),
                'feedback': feedback,
                'can_proceed': is_perfect,
                'scores': {
                    'examination_score': float(getattr(session, 'examination_score', 0) or 0),
                    'diagnosis_score': float(getattr(session, 'diagnosis_score', 0) or 0),
                    'treatment_score': float(getattr(session, 'treatment_score', 0) or 0),
                    'overall_score': float(getattr(session, 'overall_score', 0) or 0)
                },
                'overall_feedback': overall_feedback,
                'current_stage': session.session_status,
                'completion_time': session.completed_at.isoformat() if session.completed_at else None
            },
            'message': '治疗方案提交成功'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'提交失败: {str(e)}'
        }, status=500)


def calculate_rationale_score(student_rationale, correct_rationale, key_points_text):
    """
    计算治疗依据得分（0-100）
    基于：文本相似度（60%）+ 关键点覆盖度（40%）
    """
    if not correct_rationale:
        return 50.0  # 如果没有参考依据，给予基础分
    
    # 1. 文本相似度得分（60%）
    similarity = SequenceMatcher(None, student_rationale.lower(), correct_rationale.lower()).ratio()
    similarity_score = similarity * 60
    
    # 2. 关键点覆盖度得分（40%）
    key_points_score = 0
    if key_points_text:
        key_points = [kp.strip() for kp in key_points_text.split('\n') if kp.strip()]
        if key_points:
            matched_points = sum(
                1 for kp in key_points 
                if kp.lower() in student_rationale.lower()
            )
            key_points_score = (matched_points / len(key_points)) * 40
    
    total_score = similarity_score + key_points_score
    return round(total_score, 2)


def generate_treatment_feedback(is_perfect, correct_count, total_optimal, 
                                incorrect_count, rationale_score, selected_treatments):
    """生成治疗方案反馈"""
    feedback_parts = []
    
    # 1. 治疗选择反馈
    if is_perfect:
        feedback_parts.append("✓ 太好了！您选择了所有最佳治疗方案。")
    elif correct_count > 0:
        feedback_parts.append(f"您选对了 {correct_count}/{total_optimal} 个最佳治疗方案。")
        if incorrect_count > 0:
            feedback_parts.append(f"但是选择了 {incorrect_count} 个不太适合的治疗方案。")
    else:
        feedback_parts.append("很遗憾，您没有选择到最佳治疗方案。")
    
    # 2. 治疗依据反馈
    if rationale_score >= 80:
        feedback_parts.append("您的治疗依据分析得很好！")
    elif rationale_score >= 60:
        feedback_parts.append("您的治疗依据基本合理，但还可以更完善。")
    else:
        feedback_parts.append("建议您更详细地分析治疗依据。")
    
    # 3. 具体治疗方案的反馈
    if selected_treatments.exists():
        feedback_parts.append("\n您选择的治疗方案：")
        for treatment in selected_treatments:
            if treatment.selection_feedback:
                feedback_parts.append(f"• {treatment.treatment_name}: {treatment.selection_feedback}")
    
    return '\n'.join(feedback_parts)
