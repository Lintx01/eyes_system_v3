from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Avg
from django.utils import timezone
from .models import (
    ClinicalCase, ExaminationOption, DiagnosisOption, TreatmentOption, 
    StudentClinicalSession, TeachingFeedback
)
import json
from datetime import datetime, timedelta


# ==================== 检查选择验证辅助函数 ====================

def validate_examination_selection(required_exam_ids, selected_exam_ids, required_exams, session):
    """
    验证学生的检查选择是否符合要求
    要求：必须完全选中所有必选项，不能多选不能少选
    """
    missing_required = required_exam_ids - selected_exam_ids
    extra_selected = selected_exam_ids - required_exam_ids
    
    # 获取当前会话的提交次数（不是基于历史错误数量，而是实际提交次数）
    if not hasattr(session, 'session_data') or session.session_data is None:
        session.session_data = {}
    
    # 获取本次会话的提交尝试计数器
    current_attempt_count = session.session_data.get('examination_current_attempt_count', 0) + 1
    session.session_data['examination_current_attempt_count'] = current_attempt_count
    session.save()
    
    examination_errors = session.session_data.get('examination_selection_errors', [])
    attempt_count = current_attempt_count  # 使用当前会话的实际提交次数
    
    # 检查是否完全匹配
    is_valid = len(missing_required) == 0 and len(extra_selected) == 0
    
    error_message = ""
    if not is_valid:
        error_parts = []
        
        if missing_required:
            missing_names = required_exams.filter(id__in=missing_required).values_list('examination_name', flat=True)
            error_parts.append(f"缺少必选检查项目：{', '.join(missing_names)}")
        
        if extra_selected:
            # 这里需要查询所有检查项来获取额外选择的名称
            from .models import ExaminationOption
            extra_exams = ExaminationOption.objects.filter(id__in=extra_selected)
            extra_names = extra_exams.values_list('examination_name', flat=True)
            error_parts.append(f"不应选择的检查项目：{', '.join(extra_names)}")
        
        error_message = "选择有误，请检查后重新选择。" + "; ".join(error_parts)
        
        # 根据尝试次数调整提示消息
        if attempt_count == 1:
            error_message += "\n提示：请仔细阅读案例，选择最必要的检查项目。"
        elif attempt_count == 2:
            error_message += f"\n这是您第{attempt_count}次尝试，请更加仔细地分析案例需求。"
        elif attempt_count >= 3:
            error_message += f"\n这是您第{attempt_count}次尝试，建议重新阅读案例详情和检查项目描述。"
    
    # 计算惩罚分数
    penalty_applied = calculate_examination_penalty(attempt_count, len(missing_required), len(extra_selected))
    
    return {
        'is_valid': is_valid,
        'error_message': error_message,
        'missing_required': list(missing_required),
        'extra_selected': list(extra_selected),
        'attempt_count': attempt_count,
        'penalty_applied': penalty_applied
    }


def calculate_examination_penalty(attempt_count, missing_count, extra_count):
    """
    计算检查选择错误的惩罚分数
    
    Args:
        attempt_count: 错误尝试次数
        missing_count: 缺少的必选项数量
        extra_count: 多选的项目数量
    
    Returns:
        float: 惩罚分数（从总分中扣除）
    """
    base_penalty = 0
    
    # 基础惩罚：每次错误尝试
    if attempt_count == 1:
        base_penalty = 5  # 第一次错误扣5分
    elif attempt_count == 2:
        base_penalty = 10  # 第二次错误扣10分
    elif attempt_count == 3:
        base_penalty = 15  # 第三次错误扣15分
    else:
        base_penalty = 20  # 第四次及以上扣20分
    
    # 严重度惩罚：根据错误类型和数量
    severity_penalty = 0
    
    # 缺少必选项的惩罚（更严重）
    severity_penalty += missing_count * 3
    
    # 多选不必要项目的惩罚
    severity_penalty += extra_count * 2
    
    total_penalty = base_penalty + severity_penalty
    
    # 限制最大惩罚分数，避免过度惩罚
    max_penalty = min(30, total_penalty)  # 单次最多扣30分
    
    return max_penalty


def record_examination_error(session, validation_result):
    """
    记录学生检查选择的错误操作
    
    Args:
        session: StudentClinicalSession实例
        validation_result: 验证结果字典
    """
    if not hasattr(session, 'session_data') or session.session_data is None:
        session.session_data = {}
    
    if 'examination_selection_errors' not in session.session_data:
        session.session_data['examination_selection_errors'] = []
    
    # 记录错误详情
    error_record = {
        'timestamp': timezone.now().isoformat(),
        'attempt_number': validation_result['attempt_count'],
        'missing_required_count': len(validation_result['missing_required']),
        'extra_selected_count': len(validation_result['extra_selected']),
        'missing_required_ids': validation_result['missing_required'],
        'extra_selected_ids': validation_result['extra_selected'],
        'penalty_applied': validation_result['penalty_applied'],
        'error_message': validation_result['error_message']
    }
    
    session.session_data['examination_selection_errors'].append(error_record)
    
    # 应用惩罚到检查选择得分
    current_penalty = session.session_data.get('examination_selection_penalty', 0)
    new_penalty = current_penalty + validation_result['penalty_applied']
    session.session_data['examination_selection_penalty'] = new_penalty
    
    # 标记检查选择为无效
    session.examination_selection_valid = False
    session.required_examinations_completed = False
    
    # 保存会话
    session.save()
    
    # 记录到step_completion_status中
    if 'examination_selection' not in session.step_completion_status:
        session.step_completion_status['examination_selection'] = {}
    
    session.step_completion_status['examination_selection'].update({
        'error_count': len(session.session_data['examination_selection_errors']),
        'total_penalty': new_penalty,
        'last_error_time': timezone.now().isoformat()
    })
    
    session.save()


def record_examination_success(session, final_attempt_count):
    """
    记录学生成功完成检查选择
    
    Args:
        session: StudentClinicalSession实例
        final_attempt_count: 最终成功时的尝试次数
    """
    if not hasattr(session, 'session_data') or session.session_data is None:
        session.session_data = {}
    
    # 记录成功信息
    success_record = {
        'timestamp': timezone.now().isoformat(),
        'final_attempt': final_attempt_count,
        'total_errors': len(session.session_data.get('examination_selection_errors', [])),
        'total_penalty': session.session_data.get('examination_selection_penalty', 0)
    }
    
    session.session_data['examination_selection_success'] = success_record
    
    # 重置当前会话的尝试计数器（成功后重新开始计数）
    session.session_data['examination_current_attempt_count'] = 0
    
    # 更新步骤完成状态
    if 'examination_selection' not in session.step_completion_status:
        session.step_completion_status['examination_selection'] = {}
    
    session.step_completion_status['examination_selection'].update({
        'completed': True,
        'success_time': timezone.now().isoformat(),
        'attempts_needed': final_attempt_count,
        'performance_rating': calculate_performance_rating(final_attempt_count)
    })
    
    session.save()


def calculate_performance_rating(attempt_count):
    """
    根据尝试次数计算表现评级
    
    Args:
        attempt_count: 尝试次数
        
    Returns:
        str: 表现评级
    """
    if attempt_count == 1:
        return "优秀"  # 一次成功
    elif attempt_count == 2:
        return "良好"  # 两次成功
    elif attempt_count == 3:
        return "及格"  # 三次成功
    else:
        return "需要改进"  # 四次及以上


# 权限检查函数
def is_teacher(user):
    """检查用户是否为教师"""
    return user.groups.filter(name='Teachers').exists() or user.is_superuser

def is_student(user):
    """检查用户是否为学生"""
    return user.groups.filter(name='Students').exists()


# 基础视图
def login_view(request):
    """用户登录视图"""
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # 根据用户角色跳转
            if is_teacher(user):
                return redirect('teacher_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            error = '账号或密码错误'
    return render(request, 'login.html', {'error': error})


@require_POST
def logout_view(request):
    """用户退出登录视图"""
    logout(request)
    return redirect('login')


@login_required
def index(request):
    """首页 - 根据用户角色跳转"""
    if is_teacher(request.user):
        return redirect('teacher_dashboard')
    else:
        return redirect('student_dashboard')


# 学生端视图
@login_required
@user_passes_test(is_student, login_url='login')
def student_dashboard(request):
    """学生仪表板"""
    user = request.user
    
    # 临床推理病例统计
    total_clinical_cases = ClinicalCase.objects.filter(is_active=True).count()
    
    # 获取用户学习会话统计
    user_sessions = StudentClinicalSession.objects.filter(student=user)
    completed_sessions = user_sessions.filter(completed_at__isnull=False).count()
    
    # 计算学习进度百分比
    progress_percentage = 0
    if total_clinical_cases > 0:
        progress_percentage = round((completed_sessions / total_clinical_cases) * 100, 1)
    
    # 计算总学习时长（分钟）
    total_study_time = 0
    for session in user_sessions.filter(completed_at__isnull=False):
        if session.completed_at and session.started_at:
            duration = session.completed_at - session.started_at
            total_study_time += duration.total_seconds() / 60  # 转换为分钟
    total_study_time = round(total_study_time)
    
    # 最近学习记录
    recent_sessions = user_sessions.order_by('-started_at')[:5]
    
    # 模拟进度对象结构
    progress = {
        'progress_percentage': progress_percentage,
        'total_study_time': total_study_time,
    }
    
    context = {
        'total_clinical_cases': total_clinical_cases,
        'completed_sessions': completed_sessions,
        'recent_sessions': recent_sessions,
        'progress': progress,
    }
    
    return render(request, 'student/dashboard.html', context)





# 教师端视图
@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_dashboard(request):
    """教师仪表板"""
    # 临床推理病例统计
    total_clinical_cases = ClinicalCase.objects.count()
    active_clinical_cases = ClinicalCase.objects.filter(is_active=True).count()
    total_students = User.objects.filter(groups__name='Students').count()
    
    # 检查选项统计
    total_examinations = ExaminationOption.objects.count()
    
    # 学生学习统计
    total_sessions = StudentClinicalSession.objects.count()
    completed_sessions = StudentClinicalSession.objects.filter(completed_at__isnull=False).count()
    
    # 计算完成率
    completion_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0
    
    # 最近活动
    recent_sessions = StudentClinicalSession.objects.select_related('student', 'clinical_case').order_by('-started_at')[:10]
    
    context = {
        'total_clinical_cases': total_clinical_cases,
        'active_clinical_cases': active_clinical_cases,
        'total_students': total_students,
        'total_examinations': total_examinations,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'completion_rate': completion_rate,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'teacher/dashboard.html', context)


































@login_required
@user_passes_test(is_teacher, login_url='login')


















# === 临床推理系统API ===

@login_required
@user_passes_test(is_student, login_url='login')
def clinical_case_detail(request, case_id):
    """获取临床案例详情 - 病史展示阶段"""
    try:
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 获取或创建学生会话
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={'session_status': 'history'}
        )
        
        # 如果是新会话，重置状态
        if created:
            session.session_status = 'history'
            session.save()
        
        case_data = {
            'case_id': clinical_case.case_id,
            'title': clinical_case.title,
            'patient_info': {
                'age': clinical_case.patient_age,
                'gender': clinical_case.get_patient_gender_display(),
            },
            'clinical_info': {
                'chief_complaint': clinical_case.chief_complaint,
                'present_illness': clinical_case.present_illness,
                'past_history': clinical_case.past_history,
                'family_history': clinical_case.family_history,
            },
            'learning_objectives': clinical_case.learning_objectives,
            'case_images': clinical_case.case_images or [],
            'session_status': session.session_status,
            'current_stage': 'history',
            'next_stage': 'examination'
        }
        
        return JsonResponse({
            'success': True,
            'data': case_data,
            'message': '案例信息获取成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取案例信息失败：{str(e)}'
        }, status=500)






# ================== 临床推理系统API视图 ==================

@login_required
@user_passes_test(is_student, login_url='login')
def clinical_case_detail(request, case_id):
    """获取临床案例详情 - 病史展示阶段"""
    try:
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 获取或创建学生会话
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={'session_status': 'history'}
        )
        
        # 如果是新会话，重置状态
        if created:
            session.session_status = 'history'
            session.save()
        
        case_data = {
            'case_id': clinical_case.case_id,
            'title': clinical_case.title,
            'patient_info': {
                'age': clinical_case.patient_age,
                'gender': clinical_case.get_patient_gender_display(),
            },
            'clinical_info': {
                'chief_complaint': clinical_case.chief_complaint,
                'present_illness': clinical_case.present_illness,
                'past_history': clinical_case.past_history,
                'family_history': clinical_case.family_history,
            },
            'learning_objectives': clinical_case.learning_objectives,
            'case_images': clinical_case.case_images or [],
            'session_status': session.session_status,
            'current_stage': 'history',
            'next_stage': 'examination'
        }
        
        return JsonResponse({
            'success': True,
            'data': case_data,
            'message': '案例信息获取成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取案例信息失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
@require_POST
def submit_examination_choices(request):
    """提交检查选择 - 检查阶段"""
    try:
        data = json.loads(request.body)
        case_id = data.get('case_id')
        selected_examinations = data.get('selected_examinations', [])
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        session = get_object_or_404(StudentClinicalSession, 
                                  student=request.user, 
                                  clinical_case=clinical_case)
        
        # 更新会话状态
        session.selected_examinations = selected_examinations
        session.session_status = 'diagnosis'
        
        # 计算检查选择得分
        examination_options = ExaminationOption.objects.filter(clinical_case=clinical_case)
        
        # 1. 必选检查评分（60%权重）
        required_options = examination_options.filter(is_required=True)
        total_required = required_options.count()
        selected_required = required_options.filter(id__in=selected_examinations).count()
        
        if total_required > 0:
            required_score = selected_required / total_required
        else:
            required_score = 1.0  # 如果没有必选检查，给满分
        
        # 2. 检查效率评分（30%权重）- 基于检查数量和质量的合理性
        total_selected = len(selected_examinations)
        efficiency_score = 1.0
        
        # 效率评分逻辑：
        # - 选择过多检查（超过8项）会降低效率分
        # - 选择过少检查（少于2项）也会降低效率分
        # - 最优范围：2-6项检查
        if total_selected > 8:
            # 每多选一项检查扣5%
            efficiency_score -= (total_selected - 8) * 0.05
        elif total_selected < 2:
            # 检查太少扣分更重
            efficiency_score -= (2 - total_selected) * 0.2
        
        # 确保效率分不为负
        efficiency_score = max(0, efficiency_score)
        
        # 3. 统计不必要检查数量（仅用于反馈，不影响评分）
        unnecessary_examinations = []
        for exam_id in selected_examinations:
            if not examination_options.filter(
                Q(id=exam_id) & Q(is_required=True)
            ).exists():
                # 检查是否为高价值检查（诊断价值高的检查）
                exam_option = examination_options.filter(id=exam_id).first()
                if exam_option and exam_option.diagnostic_value < 2:  # 低价值检查视为不必要
                    unnecessary_examinations.append(exam_id)
        unnecessary_count = len(unnecessary_examinations)
        
        # 基础得分计算：必选检查70% + 检查效率30%
        base_examination_score = (
            required_score * 0.7 + 
            efficiency_score * 0.3
        ) * 100
        
        # 根据检查选择的最终尝试次数计算惩罚
        selection_penalty = 0
        if hasattr(session, 'session_data') and session.session_data:
            # 从成功记录中获取最终尝试次数，如果没有则从步骤完成状态中获取
            final_attempt_count = 1
            
            if 'examination_selection_success' in session.session_data:
                final_attempt_count = session.session_data['examination_selection_success'].get('final_attempt', 1)
            elif 'examination_selection' in session.step_completion_status:
                final_attempt_count = session.step_completion_status['examination_selection'].get('final_attempt', 1)
            
            # 只有当尝试次数大于1时才应用惩罚
            if final_attempt_count > 1:
                # 基于最终尝试次数计算惩罚：第2次尝试扣5分，第3次扣10分，第4次及以后扣20分
                if final_attempt_count == 2:
                    selection_penalty = 5
                elif final_attempt_count == 3:
                    selection_penalty = 10
                else:
                    selection_penalty = 20
        
        # 最终得分 = 基础得分 - 基于尝试次数的惩罚
        final_examination_score = max(0, base_examination_score - selection_penalty)
        
        session.examination_score = max(0, min(100, final_examination_score))
        session.save()
        
        # 准备得分详情用于调试和反馈
        score_details = {
            'total_score': round(session.examination_score, 1),
            'base_score': round(base_examination_score, 1),
            'selection_penalty': round(selection_penalty, 1),
            'required_score': round(required_score * 70, 1),
            'efficiency_score': round(efficiency_score * 30, 1),
            'required_stats': f"{selected_required}/{total_required}",
            'efficiency_stats': f"选择了{total_selected}项检查",
            'unnecessary_count': unnecessary_count,
            'total_selected': total_selected,
            'penalty_info': {
                'error_attempts': len(session.session_data.get('examination_selection_errors', [])) if hasattr(session, 'session_data') and session.session_data else 0,
                'penalty_applied': selection_penalty
            }
        }
        
        # 获取选择的检查结果
        selected_examination_results = []
        for exam_id in selected_examinations:
            try:
                exam_option = ExaminationOption.objects.get(id=exam_id, clinical_case=clinical_case)
                selected_examination_results.append({
                    'id': exam_option.id,
                    'name': exam_option.examination_name,
                    'type': exam_option.get_examination_type_display(),
                    'result': exam_option.actual_result,
                    'images': exam_option.result_images or [],
                    'diagnostic_value': exam_option.get_diagnostic_value_display(),
                    'is_recommended': exam_option.is_recommended
                })
            except ExaminationOption.DoesNotExist:
                continue
        
        # 获取诊断选项
        diagnosis_options = DiagnosisOption.objects.filter(
            clinical_case=clinical_case
        ).order_by('display_order')
        
        diagnosis_data = [{
            'id': option.id,
            'name': option.diagnosis_name,
            'code': option.diagnosis_code,
            'is_differential': option.is_differential,
            'probability_score': option.probability_score
        } for option in diagnosis_options]
        
        return JsonResponse({
            'success': True,
            'data': {
                'examination_results': selected_examination_results,
                'examination_score': session.examination_score,
                'score_details': score_details,
                'diagnosis_options': diagnosis_data,
                'current_stage': 'diagnosis',
                'next_stage': 'treatment'
            },
            'message': f'检查结果获取成功，检查选择得分：{session.examination_score:.1f}分'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'提交检查选择失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
@require_POST
def submit_diagnosis_choice(request):
    """提交诊断选择 - 诊断阶段"""
    try:
        data = json.loads(request.body)
        case_id = data.get('case_id')
        selected_diagnosis_id = data.get('selected_diagnosis_id')
        reasoning = data.get('reasoning', '')
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        session = get_object_or_404(StudentClinicalSession, 
                                  student=request.user, 
                                  clinical_case=clinical_case)
        
        diagnosis_option = get_object_or_404(DiagnosisOption, 
                                           id=selected_diagnosis_id, 
                                           clinical_case=clinical_case)
        
        # 更新会话状态
        session.selected_diagnosis = diagnosis_option
        session.session_status = 'treatment'
        
        # 计算诊断得分
        if diagnosis_option.is_correct_diagnosis:
            session.diagnosis_score = 100.0
            feedback_message = diagnosis_option.correct_feedback
            feedback_type = 'positive'
        else:
            session.diagnosis_score = diagnosis_option.probability_score * 100
            feedback_message = diagnosis_option.incorrect_feedback
            feedback_type = 'corrective'
        
        session.save()
        
        # 创建诊断阶段反馈
        TeachingFeedback.objects.create(
            student_session=session,
            feedback_stage='diagnosis',
            feedback_type=feedback_type,
            feedback_content=feedback_message,
            is_automated=True
        )
        
        # 获取相关的治疗选项
        treatment_options = TreatmentOption.objects.filter(
            clinical_case=clinical_case,
            related_diagnosis=diagnosis_option
        ).order_by('display_order')
        
        # 如果没有特定诊断的治疗选项，获取通用治疗选项
        if not treatment_options.exists():
            treatment_options = TreatmentOption.objects.filter(
                clinical_case=clinical_case,
                related_diagnosis__isnull=True
            ).order_by('display_order')
        
        treatment_data = [{
            'id': option.id,
            'name': option.treatment_name,
            'type': option.get_treatment_type_display(),
            'description': option.treatment_description,
            'is_optimal': option.is_optimal,
            'is_acceptable': option.is_acceptable,
            'is_contraindicated': option.is_contraindicated,
            'efficacy_score': option.get_efficacy_score_display(),
            'safety_score': option.get_safety_score_display(),
            'expected_outcome': option.expected_outcome
        } for option in treatment_options]
        
        return JsonResponse({
            'success': True,
            'data': {
                'diagnosis_feedback': feedback_message,
                'diagnosis_score': session.diagnosis_score,
                'selected_diagnosis': {
                    'name': diagnosis_option.diagnosis_name,
                    'code': diagnosis_option.diagnosis_code,
                    'is_correct': diagnosis_option.is_correct_diagnosis
                },
                'treatment_options': treatment_data,
                'current_stage': 'treatment',
                'next_stage': 'feedback'
            },
            'message': '诊断选择已提交，请选择治疗方案'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'提交诊断选择失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
@require_POST
def submit_treatment_choices(request):
    """提交治疗方案选择 - 治疗阶段"""
    try:
        data = json.loads(request.body)
        case_id = data.get('case_id')
        selected_treatments = data.get('selected_treatments', [])
        treatment_reasoning = data.get('reasoning', '')
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        session = get_object_or_404(StudentClinicalSession, 
                                  student=request.user, 
                                  clinical_case=clinical_case)
        
        # 更新会话状态
        session.selected_treatments = selected_treatments
        session.session_status = 'feedback'
        
        # 计算治疗方案得分
        treatment_options = TreatmentOption.objects.filter(
            id__in=selected_treatments,
            clinical_case=clinical_case
        )
        
        total_score = 0
        optimal_count = 0
        acceptable_count = 0
        contraindicated_count = 0
        
        treatment_feedback = []
        
        for treatment in treatment_options:
            if treatment.is_optimal:
                optimal_count += 1
                total_score += 100
            elif treatment.is_acceptable:
                acceptable_count += 1
                total_score += 70
            elif treatment.is_contraindicated:
                contraindicated_count += 1
                total_score += 0  # 禁忌治疗不加分
            else:
                total_score += 50  # 中性治疗
            
            treatment_feedback.append({
                'treatment_name': treatment.treatment_name,
                'feedback': treatment.selection_feedback,
                'is_optimal': treatment.is_optimal,
                'is_acceptable': treatment.is_acceptable,
                'is_contraindicated': treatment.is_contraindicated
            })
        
        # 计算平均分
        if len(selected_treatments) > 0:
            session.treatment_score = total_score / len(selected_treatments)
        else:
            session.treatment_score = 0
        
        # 计算总体得分
        session.calculate_overall_score()
        session.completed_at = timezone.now()
        session.session_status = 'completed'
        session.save()
        
        # 创建治疗阶段反馈
        treatment_feedback_content = f"您选择了{len(selected_treatments)}个治疗方案。"
        if optimal_count > 0:
            treatment_feedback_content += f"其中{optimal_count}个为最佳治疗。"
        if contraindicated_count > 0:
            treatment_feedback_content += f"请注意：有{contraindicated_count}个禁忌治疗需要避免。"
        
        TeachingFeedback.objects.create(
            student_session=session,
            feedback_stage='treatment',
            feedback_type='guidance',
            feedback_content=treatment_feedback_content,
            is_automated=True
        )
        
        # 创建总体反馈
        overall_feedback = f"恭喜完成临床推理！总体得分：{session.overall_score:.1f}分。"
        if session.overall_score >= 90:
            overall_feedback += "表现优秀！您展现了出色的临床思维能力。"
        elif session.overall_score >= 70:
            overall_feedback += "表现良好，继续努力提升临床推理能力。"
        else:
            overall_feedback += "还有提升空间，建议复习相关知识点。"
        
        TeachingFeedback.objects.create(
            student_session=session,
            feedback_stage='overall',
            feedback_type='encouragement',
            feedback_content=overall_feedback,
            is_automated=True
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'treatment_feedback': treatment_feedback,
                'treatment_score': session.treatment_score,
                'scores': {
                    'examination_score': session.examination_score,
                    'diagnosis_score': session.diagnosis_score,
                    'treatment_score': session.treatment_score,
                    'overall_score': session.overall_score
                },
                'overall_feedback': overall_feedback,
                'current_stage': 'completed',
                'completion_time': session.completed_at.isoformat()
            },
            'message': '临床推理学习完成！'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'提交治疗方案失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def get_clinical_learning_progress(request, case_id):
    """获取学生在特定案例中的学习进度"""
    try:
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        try:
            session = StudentClinicalSession.objects.get(
                student=request.user,
                clinical_case=clinical_case
            )
            
            # 获取相关反馈
            feedbacks = TeachingFeedback.objects.filter(
                student_session=session
            ).order_by('created_at')
            
            feedback_data = [{
                'stage': feedback.feedback_stage,
                'type': feedback.feedback_type,
                'content': feedback.feedback_content,
                'suggestions': feedback.improvement_suggestions,
                'created_at': feedback.created_at.isoformat()
            } for feedback in feedbacks]
            
            progress_data = {
                'session_status': session.session_status,
                'scores': {
                    'examination_score': session.examination_score,
                    'diagnosis_score': session.diagnosis_score,
                    'treatment_score': session.treatment_score,
                    'overall_score': session.overall_score
                },
                'learning_path': {
                    'selected_examinations': session.selected_examinations,
                    'selected_diagnosis': {
                        'id': session.selected_diagnosis.id if session.selected_diagnosis else None,
                        'name': session.selected_diagnosis.diagnosis_name if session.selected_diagnosis else None
                    },
                    'selected_treatments': session.selected_treatments
                },
                'time_tracking': {
                    'started_at': session.started_at.isoformat(),
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None,
                    'time_spent': session.time_spent
                },
                'feedbacks': feedback_data
            }
            
        except StudentClinicalSession.DoesNotExist:
            progress_data = {
                'session_status': 'not_started',
                'message': '尚未开始学习该案例'
            }
        
        return JsonResponse({
            'success': True,
            'data': progress_data,
            'message': '学习进度获取成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取学习进度失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def get_examination_options(request, case_id):
    """获取案例的检查选项列表 - 包含必选项和随机干扰项"""
    try:
        import random
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 获取该案例的必选检查项目（教师设置的标准答案）
        required_examinations = ExaminationOption.objects.filter(
            clinical_case=clinical_case,
            is_required=True
        ).order_by('display_order', 'examination_type')
        
        # 获取该案例的可选检查项目
        optional_examinations = ExaminationOption.objects.filter(
            clinical_case=clinical_case,
            is_required=False
        )
        
        # 如果没有必选项，返回该案例的所有检查项
        if not required_examinations.exists():
            all_case_examinations = ExaminationOption.objects.filter(
                clinical_case=clinical_case
            ).order_by('display_order', 'examination_type')
            
            options_data = [{
                'id': option.id,
                'type': option.get_examination_type_display(),
                'name': option.examination_name,
                'description': option.examination_description,
                'diagnostic_value': option.get_diagnostic_value_display(),
                'cost_effectiveness': option.get_cost_effectiveness_display(),
                'is_recommended': option.is_recommended,
                'is_required': option.is_required,
                'is_multiple_choice': option.is_multiple_choice,
                'images': option.result_images or [],
                'is_case_required': False,  # 没有设置必选项
                'is_distractor': False
            } for option in all_case_examinations]
            
            return JsonResponse({
                'success': True,
                'data': {
                    'examination_options': options_data,
                    'total_count': len(options_data),
                    'required_count': 0,
                    'distractor_count': 0,
                    'mode': 'standard'  # 标准模式，显示所有案例检查项
                },
                'message': '检查选项获取成功（标准模式）'
            })
        
        # 有必选项的情况：混合必选项和干扰项
        # 获取其他案例的检查项目作为干扰项池
        distractor_pool = ExaminationOption.objects.exclude(
            clinical_case=clinical_case
        )
        
        # 如果干扰项池不够，使用当前案例的可选项作为补充
        if distractor_pool.count() < 3:
            distractor_pool = optional_examinations
        
        # 按检查类型分组，确保干扰项类型多样性
        distractor_by_type = {}
        for exam in distractor_pool:
            exam_type = exam.examination_type
            if exam_type not in distractor_by_type:
                distractor_by_type[exam_type] = []
            distractor_by_type[exam_type].append(exam)
        
        # 计算需要添加的干扰项数量（根据必选项数量动态调整）
        required_count = required_examinations.count()
        if required_count <= 2:
            distractor_count = 5  # 必选项很少时多加干扰项
        elif required_count <= 4:
            distractor_count = 3  # 中等数量
        else:
            distractor_count = 2  # 必选项多时少加干扰项
        
        # 从各类型中随机选择干扰项
        selected_distractors = []
        
        # 优先从不同类型中选择
        for exam_type, exams in distractor_by_type.items():
            if len(selected_distractors) < distractor_count and exams:
                # 从每个类型中随机选1个
                selected_distractors.extend(random.sample(exams, min(1, len(exams))))
        
        # 如果还需要更多干扰项，随机选择剩余的
        if len(selected_distractors) < distractor_count:
            remaining_pool = [exam for exam in distractor_pool 
                            if exam not in selected_distractors]
            if remaining_pool:
                additional_count = min(distractor_count - len(selected_distractors), 
                                     len(remaining_pool))
                selected_distractors.extend(random.sample(remaining_pool, additional_count))
        
        # 合并必选项和干扰项
        all_examinations = list(required_examinations) + selected_distractors[:distractor_count]
        
        # 随机打乱顺序
        random.shuffle(all_examinations)
        
        # 构建返回数据
        options_data = [{
            'id': option.id,
            'type': option.get_examination_type_display(),
            'name': option.examination_name,
            'description': option.examination_description,
            'diagnostic_value': option.get_diagnostic_value_display(),
            'cost_effectiveness': option.get_cost_effectiveness_display(),
            'is_recommended': option.is_recommended,
            'is_required': option.is_required,
            'is_multiple_choice': option.is_multiple_choice,
            'images': option.result_images or [],
            # 标识是否为该案例的必选项
            'is_case_required': option.clinical_case_id == clinical_case.id and option.is_required,
            'is_distractor': option.clinical_case_id != clinical_case.id
        } for option in all_examinations]
        
        return JsonResponse({
            'success': True,
            'data': {
                'examination_options': options_data,
                'total_count': len(options_data),
                'required_count': required_count,
                'distractor_count': len(selected_distractors),
                'mode': 'mixed'  # 混合模式，包含必选项和干扰项
            },
            'message': '检查选项获取成功（含必选项和干扰项）'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取检查选项失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def get_examination_result(request, case_id, exam_id):
    """获取单个检查项目的详细结果"""
    try:
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        examination = get_object_or_404(ExaminationOption, 
                                       id=exam_id, 
                                       clinical_case=clinical_case)
        
        # 构建检查结果数据
        result_data = {
            'id': examination.id,
            'name': examination.examination_name,
            'type': examination.get_examination_type_display(),
            'description': examination.examination_description,
            'result': examination.actual_result,
            'normal_result': examination.normal_result,
            'abnormal_result': examination.abnormal_result,
            'diagnostic_value': examination.get_diagnostic_value_display(),
            'is_recommended': examination.is_recommended,
            'is_fundus_exam': examination.is_fundus_exam,
            'fundus_reminder_text': examination.fundus_reminder_text,
            # OCT检查相关字段
            'is_oct_exam': examination.is_oct_exam,
            'oct_report_text': examination.oct_report_text,
            'oct_measurement_data': examination.oct_measurement_data,
            'image_display_mode': examination.image_display_mode,
            'image_findings': examination.image_findings,
            'images': [],
            'examination_data': {}
        }
        
        # 添加图像数据
        images = []
        
        # 处理result_images字段
        if examination.result_images:
            images.extend(examination.result_images)
        
        # 处理左右眼图像
        if examination.left_eye_image:
            image_data = {
                'url': examination.left_eye_image.url,
                'description': '左眼检查图片',
                'eye': 'left'
            }
            # 如果是OCT检查，添加测量数据
            if examination.is_oct_exam and examination.oct_measurement_data:
                image_data['measurements'] = examination.oct_measurement_data
                image_data['findings'] = examination.image_findings
            images.append(image_data)
        
        if examination.right_eye_image:
            image_data = {
                'url': examination.right_eye_image.url,
                'description': '右眼检查图片', 
                'eye': 'right'
            }
            # 如果是OCT检查，添加测量数据
            if examination.is_oct_exam and examination.oct_measurement_data:
                image_data['measurements'] = examination.oct_measurement_data
                image_data['findings'] = examination.image_findings
            images.append(image_data)
        
        # 处理additional_images字段（多张图像）
        if examination.additional_images:
            for idx, additional_img in enumerate(examination.additional_images):
                if isinstance(additional_img, dict):
                    images.append(additional_img)
                else:
                    images.append({
                        'url': additional_img,
                        'description': f'附加图像 {idx + 1}',
                        'eye': 'unknown'
                    })
        
        result_data['images'] = images
        
        # 添加眼科检查数据
        examination_data = {}
        if examination.left_eye_vision:
            examination_data['left_eye_vision'] = examination.left_eye_vision
        if examination.right_eye_vision:
            examination_data['right_eye_vision'] = examination.right_eye_vision
        if examination.left_eye_pressure:
            examination_data['left_eye_pressure'] = str(examination.left_eye_pressure)
        if examination.right_eye_pressure:
            examination_data['right_eye_pressure'] = str(examination.right_eye_pressure)
        
        result_data['examination_data'] = examination_data
        
        return JsonResponse({
            'success': True,
            'data': result_data,
            'message': '检查结果获取成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取检查结果失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
@require_POST
def confirm_examination_selection(request):
    """确认检查选择并获取检查顺序 - 严格验证必选项"""
    try:
        data = json.loads(request.body)
        case_id = data.get('case_id')
        selected_examinations = data.get('selected_examinations', [])
        examination_order = data.get('examination_order', [])
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        session = get_object_or_404(StudentClinicalSession, 
                                  student=request.user, 
                                  clinical_case=clinical_case)
        
        # 验证选择的检查项目是否存在
        examination_options = ExaminationOption.objects.filter(
            clinical_case=clinical_case,
            id__in=selected_examinations
        )
        
        if len(examination_options) != len(selected_examinations):
            return JsonResponse({
                'success': False,
                'message': '选择的检查项目不存在'
            }, status=400)
        
        # 获取所有必选检查项目
        required_exams = ExaminationOption.objects.filter(
            clinical_case=clinical_case,
            is_required=True
        )
        required_exam_ids = set(required_exams.values_list('id', flat=True))
        selected_exam_ids = set(selected_examinations)
        
        # 严格验证：学生选择必须与必选项完全一致
        validation_result = validate_examination_selection(
            required_exam_ids, selected_exam_ids, required_exams, session
        )
        
        if not validation_result['is_valid']:
            # 记录错误操作并应用评分惩罚
            record_examination_error(session, validation_result)
            
            return JsonResponse({
                'success': False,
                'message': validation_result['error_message'],
                'error_details': {
                    'missing_required': validation_result.get('missing_required', []),
                    'extra_selected': validation_result.get('extra_selected', []),
                    'attempt_count': validation_result.get('attempt_count', 0),
                    'penalty_applied': validation_result.get('penalty_applied', 0)
                }
            }, status=400)
        
        # 验证通过 - 记录成功状态并保存选择
        record_examination_success(session, validation_result['attempt_count'])
        
        # 保存选择的检查项目和顺序
        session.selected_examinations = selected_examinations
        session.examination_selection_valid = True
        session.required_examinations_completed = True
        
        # 将检查顺序保存在会话数据中
        if not hasattr(session, 'session_data') or session.session_data is None:
            session.session_data = {}
        
        session.session_data['examination_order'] = examination_order
        session.session_data['current_examination_index'] = 0
        
        # 记录成功完成时间
        session.step_completion_status['examination_selection'] = session.step_completion_status.get('examination_selection', {})
        session.step_completion_status['examination_selection'].update({
            'completed': True,
            'completion_time': timezone.now().isoformat(),
            'final_attempt': validation_result['attempt_count'],
            'validation_success': True
        })
        
        session.save()
        
        # 计算当前应用的惩罚（用于显示）
        total_penalty = session.session_data.get('examination_selection_penalty', 0)
        error_count = len(session.session_data.get('examination_selection_errors', []))
        
        # 构建成功消息
        if validation_result['attempt_count'] == 1:
            success_message = '检查选择已确认，准备开始检查 - 首次选择正确！'
        elif error_count > 0:
            success_message = f'检查选择已确认，准备开始检查 - 经过{validation_result["attempt_count"]}次尝试成功完成'
        else:
            success_message = '检查选择已确认，准备开始检查'

        return JsonResponse({
            'success': True,
            'data': {
                'selected_count': len(selected_examinations),
                'examination_order': examination_order,
                'message': success_message,
                'validation_info': {
                    'attempt_count': validation_result['attempt_count'],
                    'penalty_applied': total_penalty if error_count > 0 else 0,  # 只有错误时才返回扣分
                    'error_count': error_count
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'确认检查选择失败：{str(e)}'
        }, status=500)



@login_required
@user_passes_test(is_student, login_url='login')
def clinical_cases_list(request):
    """返回临床案例列表（用于前端案例库）"""
    try:
        difficulty = request.GET.get('difficulty')
        qs = ClinicalCase.objects.filter(is_active=True)
        if difficulty in ['beginner', 'intermediate', 'advanced']:
            qs = qs.filter(difficulty_level=difficulty)

        cases = []
        for c in qs.order_by('-created_at'):
            # 尝试获取学生会话以显示进度
            try:
                session = StudentClinicalSession.objects.get(student=request.user, clinical_case=c)
                status = session.session_status
                overall = session.overall_score
            except StudentClinicalSession.DoesNotExist:
                status = 'not_started'
                overall = 0

            cases.append({
                'case_id': c.case_id,
                'title': c.title,
                'patient_age': c.patient_age,
                'patient_gender': c.get_patient_gender_display(),
                'chief_complaint': c.chief_complaint[:120],
                'learning_objectives': c.learning_objectives or [],
                'case_images': c.case_images or [],
                'difficulty_level': c.difficulty_level,
                'status': status,
                'progress': {'overall_score': overall}
            })

        return JsonResponse({'success': True, 'data': {'cases': cases}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def clinical_user_stats(request):
    """返回当前学生的临床学习统计数据"""
    try:
        total_completed = StudentClinicalSession.objects.filter(student=request.user, session_status='completed').count()
        avg_overall = StudentClinicalSession.objects.filter(student=request.user, overall_score__gt=0).aggregate(Avg('overall_score'))['overall_score__avg'] or 0

        stats = {
            'completed_cases': total_completed,
            'average_score': round(avg_overall, 2),
            'difficulty_progress': {
                'beginner': {'completed': StudentClinicalSession.objects.filter(student=request.user, clinical_case__difficulty_level='beginner', session_status='completed').count(), 'total': ClinicalCase.objects.filter(difficulty_level='beginner', is_active=True).count()},
                'intermediate': {'completed': StudentClinicalSession.objects.filter(student=request.user, clinical_case__difficulty_level='intermediate', session_status='completed').count(), 'total': ClinicalCase.objects.filter(difficulty_level='intermediate', is_active=True).count()},
                'advanced': {'completed': StudentClinicalSession.objects.filter(student=request.user, clinical_case__difficulty_level='advanced', session_status='completed').count(), 'total': ClinicalCase.objects.filter(difficulty_level='advanced', is_active=True).count()},
            }
        }
        return JsonResponse({'success': True, 'data': stats})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def clinical_case_list_view(request):
    """学生端临床推理案例列表页面"""
    return render(request, 'student/clinical_case_list.html')


@login_required
def clinical_debug_view(request):
    """临床推理调试页面"""
    return render(request, 'student/clinical_debug.html')


@login_required
@user_passes_test(is_student, login_url='login')
def student_clinical_view(request, case_id):
    """学生端临床推理学习页面（渲染模板，前端通过API驱动）"""
    clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
    context = {
        'clinical_case': clinical_case
    }
    return render(request, 'student/clinical_case_detail.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def save_clinical_progress(request):
    """保存学生的临床推理学习进度"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        case_id = data.get('case_id')
        progress_data = data.get('progress_data')
        
        if not case_id or not progress_data:
            return JsonResponse({'success': False, 'message': '缺少必要参数'}, status=400)
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 获取或创建学习会话
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={
                'session_status': 'in_progress',
                'step_data': progress_data,
                'start_time': timezone.now()
            }
        )
        
        if not created:
            # 更新现有会话
            session.step_data = progress_data
            session.session_status = 'in_progress'
            session.save()
        
        return JsonResponse({'success': True, 'message': '进度已保存'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def get_clinical_progress(request, case_id):
    """获取学生的临床推理学习进度"""
    try:
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        try:
            session = StudentClinicalSession.objects.get(
                student=request.user,
                clinical_case=clinical_case
            )
            progress_data = session.step_data or {}
            return JsonResponse({'success': True, 'data': progress_data})
        except StudentClinicalSession.DoesNotExist:
            return JsonResponse({'success': True, 'data': None})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def reset_clinical_progress(request):
    """重置学生的临床推理学习进度"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        case_id = data.get('case_id')
        
        if not case_id:
            return JsonResponse({'success': False, 'message': '缺少案例ID'}, status=400)
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        
        # 删除现有会话或重置为初始状态
        try:
            session = StudentClinicalSession.objects.get(
                student=request.user,
                clinical_case=clinical_case
            )
            session.delete()
        except StudentClinicalSession.DoesNotExist:
            pass
        
        return JsonResponse({'success': True, 'message': '进度已重置'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ==================== 教师端临床推理病例管理 ====================

@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_clinical_case_list(request):
    """教师端 - 临床推理病例列表"""
    
    cases = ClinicalCase.objects.all().order_by('-created_at')
    
    # 搜索功能
    search_query = request.GET.get('search', '')
    if search_query:
        cases = cases.filter(
            Q(title__icontains=search_query) |
            Q(chief_complaint__icontains=search_query) |
            Q(present_illness__icontains=search_query)
        )
    
    # 难度筛选
    difficulty_filter = request.GET.get('difficulty', '')
    if difficulty_filter:
        cases = cases.filter(difficulty_level=difficulty_filter)
    
    # 状态筛选
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        cases = cases.filter(is_active=True)
    elif status_filter == 'inactive':
        cases = cases.filter(is_active=False)
    
    # 为每个病例添加统计数据
    from django.db.models import Count
    cases = cases.annotate(
        examination_count=Count('examination_options'),
        diagnosis_count=Count('diagnosis_options'),
        treatment_count=Count('treatment_options'),
        student_sessions_count=Count('studentclinicalsession')
    )
    
    # 分页
    from django.core.paginator import Paginator
    paginator = Paginator(cases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 为分页后的每个病例计算详细统计
    for case in page_obj:
        # 计算完成的会话数
        completed_sessions = StudentClinicalSession.objects.filter(
            clinical_case=case, 
            completed_at__isnull=False
        ).count()
        
        # 计算完成率
        total_sessions = case.student_sessions_count
        case.completion_rate = round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0)
        
        # 计算平均分 (暂时设为0，需要后续实现评分系统)
        case.avg_score = 0
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'difficulty_filter': difficulty_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'teacher/clinical_case_list.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_clinical_case_create(request):
    """教师端 - 创建临床推理病例"""
    
    if request.method == 'POST':
        try:
            # 基础信息
            title = request.POST.get('title')
            chief_complaint = request.POST.get('chief_complaint')
            present_illness = request.POST.get('present_illness')
            past_history = request.POST.get('past_history', '')
            family_history = request.POST.get('family_history', '')
            personal_history = request.POST.get('personal_history', '')
            
            # 患者信息
            patient_age = request.POST.get('patient_age')
            patient_gender = request.POST.get('patient_gender')
            patient_occupation = request.POST.get('patient_occupation', '')
            
            patient_info = {
                'age': patient_age,
                'gender': patient_gender,
                'occupation': patient_occupation
            }
            
            # 教学配置
            teaching_objectives = request.POST.get('teaching_objectives')
            difficulty_level = request.POST.get('difficulty_level')
            standard_diagnosis = request.POST.get('standard_diagnosis')
            treatment_plan = request.POST.get('treatment_plan')
            prognosis = request.POST.get('prognosis', '')
            
            # 关键知识点（JSON格式）
            key_points_text = request.POST.get('key_points', '')
            key_points = []
            if key_points_text:
                key_points = [point.strip() for point in key_points_text.split('\n') if point.strip()]
            
            # 常见错误（JSON格式）
            common_mistakes_text = request.POST.get('common_mistakes', '')
            common_mistakes = []
            if common_mistakes_text:
                common_mistakes = [mistake.strip() for mistake in common_mistakes_text.split('\n') if mistake.strip()]
            
            # 参考资料（JSON格式）
            references_text = request.POST.get('references', '')
            references = []
            if references_text:
                references = [ref.strip() for ref in references_text.split('\n') if ref.strip()]
            
            # 生成唯一的案例编号
            import uuid
            case_id = f"CC{str(uuid.uuid4())[:8].upper()}"
            
            # 创建病例
            clinical_case = ClinicalCase.objects.create(
                title=title,
                case_id=case_id,
                patient_age=patient_age,
                patient_gender=patient_gender,
                chief_complaint=chief_complaint,
                present_illness=present_illness,
                past_history=past_history,
                family_history=family_history,
                learning_objectives=key_points,
                difficulty_level=difficulty_level,
                created_by=request.user
            )
            
            messages.success(request, f'临床推理病例 "{title}" 创建成功！')
            return redirect('teacher_clinical_case_list')
            
        except Exception as e:
            messages.error(request, f'创建失败：{str(e)}')
    
    context = {
        'difficulty_choices': ClinicalCase._meta.get_field('difficulty_level').choices,
    }
    
    return render(request, 'teacher/clinical_case_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login') 
def teacher_clinical_case_edit(request, case_id):
    """教师端 - 编辑临床推理病例"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    
    if request.method == 'POST':
        try:
            # 更新基础信息
            case.title = request.POST.get('title')
            case.chief_complaint = request.POST.get('chief_complaint')
            case.present_illness = request.POST.get('present_illness')
            case.past_history = request.POST.get('past_history', '')
            case.family_history = request.POST.get('family_history', '')
            case.personal_history = request.POST.get('personal_history', '')
            
            # 更新患者信息
            patient_age = request.POST.get('patient_age')
            patient_gender = request.POST.get('patient_gender')
            patient_occupation = request.POST.get('patient_occupation', '')
            
            case.patient_info = {
                'age': patient_age,
                'gender': patient_gender,
                'occupation': patient_occupation
            }
            
            # 更新教学配置  
            case.patient_age = request.POST.get('patient_age')
            case.patient_gender = request.POST.get('patient_gender')
            case.difficulty_level = request.POST.get('difficulty_level')
            case.is_active = request.POST.get('is_active') == 'on'  # 处理复选框
            
            # 更新学习目标
            learning_objectives_text = request.POST.get('learning_objectives', '')
            if learning_objectives_text:
                case.learning_objectives = [point.strip() for point in learning_objectives_text.split('\n') if point.strip()]
            
            # 保存更改
            case.save()
            
            messages.success(request, f'临床推理病例 "{case.title}" 更新成功！')
            return redirect('teacher_clinical_case_list')
            
        except Exception as e:
            messages.error(request, f'更新失败：{str(e)}')
    
    # 准备表单数据
    context = {
        'case': case,
        'difficulty_choices': ClinicalCase._meta.get_field('difficulty_level').choices,
        'is_edit': True,
    }
    
    return render(request, 'teacher/clinical_case_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_clinical_case_delete(request, case_id):
    """教师端 - 删除临床推理病例"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    
    # 获取相关数据统计
    student_sessions_count = StudentClinicalSession.objects.filter(clinical_case=case).count()
    completed_sessions_count = StudentClinicalSession.objects.filter(
        clinical_case=case, 
        completed_at__isnull=False
    ).count()
    
    if request.method == 'POST':
        case_title = case.title
        case.delete()
        messages.success(request, f'临床推理病例 "{case_title}" 已删除')
        return redirect('teacher_clinical_case_list')
    
    context = {
        'case': case,
        'student_sessions_count': student_sessions_count,
        'completed_sessions_count': completed_sessions_count,
    }
    return render(request, 'teacher/clinical_case_delete.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_clinical_case_preview(request, case_id):
    """教师端 - 预览临床推理病例"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    
    context = {
        'case': case,
    }
    
    return render(request, 'teacher/clinical_case_preview.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_examination_options(request, case_id):
    """教师端 - 管理病例的检查选项"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    examinations = ExaminationOption.objects.filter(clinical_case=case).order_by('examination_type', 'display_order')
    
    # 计算统计信息
    required_count = examinations.filter(is_required=True).count()
    optional_count = examinations.filter(is_required=False).count()
    
    context = {
        'case': case,
        'examinations': examinations,
        'required_count': required_count,
        'optional_count': optional_count,
    }
    
    return render(request, 'teacher/examination_options.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_batch_set_required(request, case_id):
    """教师端 - 批量设置必选检查项目"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'}, status=405)
    
    try:
        case = get_object_or_404(ClinicalCase, case_id=case_id)
        
        # 获取选中的检查项目ID列表
        required_examination_ids = request.POST.getlist('required_examinations')
        
        # 重置所有检查项目为非必选
        ExaminationOption.objects.filter(clinical_case=case).update(is_required=False)
        
        # 设置选中的检查项目为必选
        if required_examination_ids:
            ExaminationOption.objects.filter(
                clinical_case=case, 
                id__in=required_examination_ids
            ).update(is_required=True)
        
        required_count = len(required_examination_ids)
        
        return JsonResponse({
            'success': True,
            'message': f'成功设置 {required_count} 个必选检查项目',
            'required_count': required_count,
            'case_id': case_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'设置失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_examination_create(request, case_id):
    """教师端 - 创建检查选项"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    
    if request.method == 'POST':
        try:
            # 创建检查选项基本信息
            examination = ExaminationOption.objects.create(
                clinical_case=case,
                examination_type=request.POST.get('examination_type'),
                examination_name=request.POST.get('examination_name'),
                examination_description=request.POST.get('examination_description'),
                normal_result=request.POST.get('normal_result'),
                abnormal_result=request.POST.get('abnormal_result'),
                actual_result=request.POST.get('actual_result'),
                diagnostic_value=int(request.POST.get('diagnostic_value', 0)),
                cost_effectiveness=int(request.POST.get('cost_effectiveness', 0)),
                is_required=request.POST.get('is_required') == 'on',
                is_recommended=request.POST.get('is_recommended') == 'on',
                is_fundus_exam=request.POST.get('is_fundus_exam') == 'on',
                display_order=int(request.POST.get('display_order', 0))
            )
            
            # 处理基础眼科检查数据
            if examination.examination_type == 'basic':
                examination.left_eye_vision = request.POST.get('left_eye_vision', '')
                examination.right_eye_vision = request.POST.get('right_eye_vision', '')
                if request.POST.get('left_eye_pressure'):
                    examination.left_eye_pressure = float(request.POST.get('left_eye_pressure'))
                if request.POST.get('right_eye_pressure'):
                    examination.right_eye_pressure = float(request.POST.get('right_eye_pressure'))
            
            # 处理OCT检查特殊字段
            if examination.examination_type == 'oct':
                examination.is_oct_exam = True
                examination.oct_report_text = request.POST.get('oct_report_text', '')
                
                # 处理OCT测量数据（JSON格式）
                oct_measurement_str = request.POST.get('oct_measurement_data', '')
                if oct_measurement_str:
                    try:
                        import json
                        examination.oct_measurement_data = json.loads(oct_measurement_str)
                    except json.JSONDecodeError:
                        pass  # 如果JSON格式错误，保持为空
            
            # 处理图像上传（OCT和眼底检查）
            if examination.examination_type in ['oct', 'fundus']:
                # 处理左眼图像
                if 'left_eye_image' in request.FILES:
                    examination.left_eye_image = request.FILES['left_eye_image']
                
                # 处理右眼图像  
                if 'right_eye_image' in request.FILES:
                    examination.right_eye_image = request.FILES['right_eye_image']
                
                # 先保存对象以获得ID
                examination.save()
                
                # 处理附加图像（多文件上传）
                additional_files = request.FILES.getlist('additional_images')
                if additional_files:
                    import os
                    from django.conf import settings
                    from django.core.files.storage import default_storage
                    
                    additional_images = []
                    for i, file in enumerate(additional_files):
                        # 生成文件路径
                        file_extension = os.path.splitext(file.name)[1]
                        filename = f'additional_{examination.id}_{i}{file_extension}'
                        file_path = f'examination_images/{filename}'
                        
                        # 保存文件
                        saved_path = default_storage.save(file_path, file)
                        
                        # 记录图像信息
                        additional_images.append({
                            'url': f'/media/{saved_path}',
                            'description': f'附加图像 {i+1}',
                            'filename': file.name,
                            'eye': 'unknown'
                        })
                    examination.additional_images = additional_images
            
            examination.save()
            
            messages.success(request, f'检查选项 "{examination.examination_name}" 创建成功！')
            return redirect('teacher_examination_options', case_id=case_id)
            
        except Exception as e:
            messages.error(request, f'创建失败：{str(e)}')
    
    context = {
        'case': case,
        'examination_type_choices': ExaminationOption._meta.get_field('examination_type').choices,
    }
    
    return render(request, 'teacher/examination_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_examination_edit(request, exam_id):
    """教师端 - 编辑检查选项"""
    
    examination = get_object_or_404(ExaminationOption, id=exam_id)
    
    if request.method == 'POST':
        try:
            # 更新基本信息
            examination.examination_type = request.POST.get('examination_type')
            examination.examination_name = request.POST.get('examination_name')
            examination.examination_description = request.POST.get('examination_description')
            examination.normal_result = request.POST.get('normal_result')
            examination.abnormal_result = request.POST.get('abnormal_result')
            examination.actual_result = request.POST.get('actual_result')
            examination.diagnostic_value = int(request.POST.get('diagnostic_value', 0))
            examination.cost_effectiveness = int(request.POST.get('cost_effectiveness', 0))
            examination.is_required = request.POST.get('is_required') == 'on'
            examination.is_recommended = request.POST.get('is_recommended') == 'on'
            examination.is_fundus_exam = request.POST.get('is_fundus_exam') == 'on'
            examination.display_order = int(request.POST.get('display_order', 0))
            
            # 处理基础眼科检查数据
            if examination.examination_type == 'basic':
                examination.left_eye_vision = request.POST.get('left_eye_vision', '')
                examination.right_eye_vision = request.POST.get('right_eye_vision', '')
                if request.POST.get('left_eye_pressure'):
                    examination.left_eye_pressure = float(request.POST.get('left_eye_pressure'))
                if request.POST.get('right_eye_pressure'):
                    examination.right_eye_pressure = float(request.POST.get('right_eye_pressure'))
            
            # 处理OCT检查特殊字段
            if examination.examination_type == 'oct':
                examination.is_oct_exam = True
                examination.oct_report_text = request.POST.get('oct_report_text', '')
                
                # 处理OCT测量数据（JSON格式）
                oct_measurement_str = request.POST.get('oct_measurement_data', '')
                if oct_measurement_str:
                    try:
                        import json
                        examination.oct_measurement_data = json.loads(oct_measurement_str)
                    except json.JSONDecodeError:
                        pass  # 如果JSON格式错误，保持原值
            else:
                # 如果不是OCT检查，清除OCT相关字段
                examination.is_oct_exam = False
                examination.oct_report_text = ''
                examination.oct_measurement_data = None
            
            # 处理图像上传（OCT和眼底检查）
            if examination.examination_type in ['oct', 'fundus']:
                # 处理左眼图像更新
                if 'left_eye_image' in request.FILES:
                    examination.left_eye_image = request.FILES['left_eye_image']
                
                # 处理右眼图像更新
                if 'right_eye_image' in request.FILES:
                    examination.right_eye_image = request.FILES['right_eye_image']
                
                # 处理附加图像更新（多文件上传）
                additional_files = request.FILES.getlist('additional_images')
                if additional_files:
                    import os
                    from django.conf import settings
                    from django.core.files.storage import default_storage
                    
                    additional_images = []
                    for i, file in enumerate(additional_files):
                        # 生成文件路径
                        file_extension = os.path.splitext(file.name)[1]
                        filename = f'additional_{examination.id}_{i}{file_extension}'
                        file_path = f'examination_images/{filename}'
                        
                        # 保存文件
                        saved_path = default_storage.save(file_path, file)
                        
                        # 记录图像信息
                        additional_images.append({
                            'url': f'/media/{saved_path}',
                            'description': f'附加图像 {i+1}',
                            'filename': file.name,
                            'eye': 'unknown'
                        })
                    examination.additional_images = additional_images
            else:
                # 如果不是影像检查，清除图像字段（但保留已有图像，除非明确删除）
                pass  # 保留现有图像，让用户明确选择是否删除
            
            examination.save()
            
            messages.success(request, f'检查选项 "{examination.examination_name}" 更新成功！')
            return redirect('teacher_examination_options', case_id=examination.clinical_case.case_id)
            
        except Exception as e:
            messages.error(request, f'更新失败：{str(e)}')
    
    # 格式化OCT测量数据为JSON字符串
    oct_measurement_json = ""
    if examination.oct_measurement_data:
        import json
        try:
            oct_measurement_json = json.dumps(examination.oct_measurement_data, indent=2, ensure_ascii=False)
        except:
            oct_measurement_json = ""
    
    context = {
        'examination': examination,
        'case': examination.clinical_case,
        'examination_type_choices': ExaminationOption._meta.get_field('examination_type').choices,
        'oct_measurement_json': oct_measurement_json,
        'is_edit': True,
    }
    
    return render(request, 'teacher/examination_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_examination_delete(request, exam_id):
    """教师端 - 删除检查选项"""
    
    examination = get_object_or_404(ExaminationOption, id=exam_id)
    case_id = examination.clinical_case.case_id
    
    if request.method == 'POST':
        exam_name = examination.examination_name
        examination.delete()
        messages.success(request, f'检查选项 "{exam_name}" 已删除')
        return redirect('teacher_examination_options', case_id=case_id)
    
    context = {
        'examination': examination,
        'case': examination.clinical_case,
    }
    
    return render(request, 'teacher/examination_delete.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_diagnosis_options(request, case_id):
    """教师端 - 诊断选项管理"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    diagnosis_options = DiagnosisOption.objects.filter(clinical_case=case).order_by('display_order')
    
    context = {
        'case': case,
        'diagnosis_options': diagnosis_options,
    }
    
    return render(request, 'teacher/diagnosis_options.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_diagnosis_create(request, case_id):
    """教师端 - 创建诊断选项"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    
    if request.method == 'POST':
        try:
            diagnosis_option = DiagnosisOption.objects.create(
                clinical_case=case,
                diagnosis_name=request.POST.get('diagnosis_name'),
                diagnosis_code=request.POST.get('icd_code', ''),
                is_correct_diagnosis=request.POST.get('is_correct') == 'on',
                probability_score=float(request.POST.get('probability', 0)) / 100.0,  # 转换为0-1范围
                supporting_evidence=request.POST.get('supporting_evidence', ''),
                contradicting_evidence=request.POST.get('contradicting_evidence', ''),
                correct_feedback=request.POST.get('educational_feedback', ''),
                incorrect_feedback=request.POST.get('educational_feedback', ''),  # 暂时使用同样的反馈
                typical_symptoms=[],  # 空的JSON列表
                typical_signs=[],     # 空的JSON列表
                display_order=int(request.POST.get('order', 0))
            )
            
            messages.success(request, f'诊断选项 "{diagnosis_option.diagnosis_name}" 创建成功！')
            return redirect('teacher_diagnosis_options', case_id=case_id)
            
        except Exception as e:
            messages.error(request, f'创建失败：{str(e)}')
    
    context = {
        'case': case,
    }
    
    return render(request, 'teacher/diagnosis_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_diagnosis_edit(request, diagnosis_id):
    """教师端 - 编辑诊断选项"""
    
    diagnosis = get_object_or_404(DiagnosisOption, id=diagnosis_id)
    
    if request.method == 'POST':
        try:
            diagnosis.diagnosis_name = request.POST.get('diagnosis_name')
            diagnosis.diagnosis_code = request.POST.get('icd_code', '')
            diagnosis.is_correct_diagnosis = request.POST.get('is_correct') == 'on'
            diagnosis.probability_score = float(request.POST.get('probability', 0)) / 100.0
            diagnosis.supporting_evidence = request.POST.get('supporting_evidence', '')
            diagnosis.contradicting_evidence = request.POST.get('contradicting_evidence', '')
            diagnosis.correct_feedback = request.POST.get('educational_feedback', '')
            diagnosis.incorrect_feedback = request.POST.get('educational_feedback', '')
            diagnosis.display_order = int(request.POST.get('order', 0))
            
            diagnosis.save()
            
            messages.success(request, f'诊断选项 "{diagnosis.diagnosis_name}" 更新成功！')
            return redirect('teacher_diagnosis_options', case_id=diagnosis.clinical_case.case_id)
            
        except Exception as e:
            messages.error(request, f'更新失败：{str(e)}')
    
    context = {
        'diagnosis': diagnosis,
        'case': diagnosis.clinical_case,
        'is_edit': True,
    }
    
    return render(request, 'teacher/diagnosis_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_diagnosis_delete(request, diagnosis_id):
    """教师端 - 删除诊断选项"""
    
    diagnosis = get_object_or_404(DiagnosisOption, id=diagnosis_id)
    case_id = diagnosis.clinical_case.case_id
    
    if request.method == 'POST':
        diagnosis_name = diagnosis.diagnosis_name
        diagnosis.delete()
        messages.success(request, f'诊断选项 "{diagnosis_name}" 已删除')
        return redirect('teacher_diagnosis_options', case_id=case_id)
    
    context = {
        'diagnosis': diagnosis,
        'case': diagnosis.clinical_case,
    }
    
    return render(request, 'teacher/diagnosis_delete.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_treatment_options(request, case_id):
    """教师端 - 治疗方案管理"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    treatment_options = TreatmentOption.objects.filter(clinical_case=case).order_by('display_order')
    
    context = {
        'case': case,
        'treatment_options': treatment_options,
    }
    
    return render(request, 'teacher/treatment_options.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_treatment_create(request, case_id):
    """教师端 - 创建治疗方案"""
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    
    if request.method == 'POST':
        try:
            treatment_option = TreatmentOption.objects.create(
                clinical_case=case,
                treatment_name=request.POST.get('treatment_name'),
                treatment_type=request.POST.get('treatment_type'),
                treatment_description=request.POST.get('description', ''),
                is_optimal=request.POST.get('is_optimal') == 'on',
                is_acceptable=request.POST.get('is_acceptable') == 'on',
                efficacy_score=int(request.POST.get('efficacy_score', 2)),
                safety_score=int(request.POST.get('safety_score', 2)),
                cost_score=int(request.POST.get('cost_score', 2)),
                expected_outcome=request.POST.get('expected_outcome', ''),
                potential_complications=request.POST.get('potential_complications', ''),
                selection_feedback=request.POST.get('selection_feedback', ''),
                display_order=int(request.POST.get('order', 0))
            )
            
            messages.success(request, f'治疗方案 "{treatment_option.treatment_name}" 创建成功！')
            return redirect('teacher_treatment_options', case_id=case_id)
            
        except Exception as e:
            messages.error(request, f'创建失败：{str(e)}')
    
    # 获取治疗类型选择
    treatment_type_choices = TreatmentOption._meta.get_field('treatment_type').choices
    efficacy_score_choices = TreatmentOption._meta.get_field('efficacy_score').choices
    safety_score_choices = TreatmentOption._meta.get_field('safety_score').choices
    cost_score_choices = TreatmentOption._meta.get_field('cost_score').choices
    
    context = {
        'case': case,
        'treatment_type_choices': treatment_type_choices,
        'efficacy_score_choices': efficacy_score_choices,
        'safety_score_choices': safety_score_choices,
        'cost_score_choices': cost_score_choices,
    }
    
    return render(request, 'teacher/treatment_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_treatment_edit(request, treatment_id):
    """教师端 - 编辑治疗方案"""
    
    treatment = get_object_or_404(TreatmentOption, id=treatment_id)
    
    if request.method == 'POST':
        try:
            treatment.treatment_name = request.POST.get('treatment_name')
            treatment.treatment_type = request.POST.get('treatment_type')
            treatment.treatment_description = request.POST.get('description', '')
            treatment.is_optimal = request.POST.get('is_optimal') == 'on'
            treatment.is_acceptable = request.POST.get('is_acceptable') == 'on'
            treatment.efficacy_score = int(request.POST.get('efficacy_score', 2))
            treatment.safety_score = int(request.POST.get('safety_score', 2))
            treatment.cost_score = int(request.POST.get('cost_score', 2))
            treatment.expected_outcome = request.POST.get('expected_outcome', '')
            treatment.potential_complications = request.POST.get('potential_complications', '')
            treatment.selection_feedback = request.POST.get('selection_feedback', '')
            treatment.display_order = int(request.POST.get('order', 0))
            
            treatment.save()
            
            messages.success(request, f'治疗方案 "{treatment.treatment_name}" 更新成功！')
            return redirect('teacher_treatment_options', case_id=treatment.clinical_case.case_id)
            
        except Exception as e:
            messages.error(request, f'更新失败：{str(e)}')
    
    # 获取选择项
    treatment_type_choices = TreatmentOption._meta.get_field('treatment_type').choices
    efficacy_score_choices = TreatmentOption._meta.get_field('efficacy_score').choices
    safety_score_choices = TreatmentOption._meta.get_field('safety_score').choices
    cost_score_choices = TreatmentOption._meta.get_field('cost_score').choices
    
    context = {
        'treatment': treatment,
        'case': treatment.clinical_case,
        'treatment_type_choices': treatment_type_choices,
        'efficacy_score_choices': efficacy_score_choices,
        'safety_score_choices': safety_score_choices,
        'cost_score_choices': cost_score_choices,
        'is_edit': True,
    }
    
    return render(request, 'teacher/treatment_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_treatment_delete(request, treatment_id):
    """教师端 - 删除治疗方案"""
    
    treatment = get_object_or_404(TreatmentOption, id=treatment_id)
    case_id = treatment.clinical_case.case_id
    
    if request.method == 'POST':
        treatment_name = treatment.treatment_name
        treatment.delete()
        messages.success(request, f'治疗方案 "{treatment_name}" 已删除')
        return redirect('teacher_treatment_options', case_id=case_id)
    
    context = {
        'treatment': treatment,
        'case': treatment.clinical_case,
    }
    
    return render(request, 'teacher/treatment_delete.html', context)
