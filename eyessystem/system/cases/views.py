from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.db.models import Q, Avg
from django.utils import timezone
from django.conf import settings
from .models import (
    ClinicalCase, ExaminationOption, DiagnosisOption, TreatmentOption, 
    StudentClinicalSession, TeachingFeedback
)
from .models import ChatMessage, PatientResponseTemplate
import json
import re
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt


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
        missing_count = len(missing_required)
        extra_count = len(extra_selected)
        
        # 构建引导性的教学反馈，而不是直接给出答案
        if attempt_count == 1:
            # 第一次尝试：提供总体指导
            if missing_count > 0 and extra_count > 0:
                error_message = f"您的检查选择需要调整。看起来您遗漏了{missing_count}项重要检查，同时选择了{extra_count}项可能不是最优的检查。"
                error_message += "\n💡 建议：重新审视患者的主要症状和体征，思考哪些检查对确诊最为关键。"
            elif missing_count > 0:
                error_message = f"您还需要选择{missing_count}项重要的检查项目。"
                error_message += "\n💡 建议：回顾患者的主诉和症状，考虑还需要哪些基础检查来评估病情。"
            elif extra_count > 0:
                error_message = f"您选择的检查项目中有{extra_count}项可能不是当前最必要的。"
                error_message += "\n💡 建议：考虑哪些检查对当前症状的诊断最有价值，避免过度检查。"
                
        elif attempt_count == 2:
            # 第二次尝试：提供更具体的思考方向
            if missing_count > 0 and extra_count > 0:
                error_message = f"检查选择仍有改进空间。您可能遗漏了{missing_count}项关键检查，并且选择了{extra_count}项可选检查。"
                error_message += "\n🎯 思考方向：\n• 患者的主要症状指向哪些系统？\n• 哪些是诊断该症状的'金标准'检查？\n• 是否选择了一些价值不高的辅助检查？"
            elif missing_count > 0:
                error_message = f"仍然缺少{missing_count}项重要检查。"
                error_message += "\n🎯 提示：仔细分析患者症状的特点，思考遗漏了哪些基础但关键的检查项目。"
            elif extra_count > 0:
                error_message = f"选择中包含了{extra_count}项非必需的检查。"
                error_message += "\n🎯 提示：优先考虑成本效益高、诊断价值大的检查项目。"
                
        else:
            # 第三次及以上：提供学习策略建议
            if missing_count > 0 and extra_count > 0:
                error_message = f"经过{attempt_count}次尝试，检查选择仍需完善。缺少{missing_count}项，多选了{extra_count}项。"
                error_message += "\n📚 学习建议：\n• 重新阅读病例的关键信息\n• 思考该疾病的标准诊断流程\n• 区分'必需检查'和'辅助检查'\n• 参考检查项目的诊断价值和成本效益标识"
            elif missing_count > 0:
                error_message = f"第{attempt_count}次尝试，仍缺少{missing_count}项关键检查。"
                error_message += "\n📚 建议：系统回顾该症状的标准检查流程，确保没有遗漏基础检查项目。"
            elif extra_count > 0:
                error_message = f"第{attempt_count}次尝试，仍包含{extra_count}项非必需检查。"
                error_message += "\n📚 建议：重新评估每项检查的必要性，优先选择诊断价值最高的项目。"
    
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
    # 简化惩罚逻辑：第一次错误只扣5分，后续递增
    if attempt_count == 1:
        return 5  # 第一次错误扣5分
    elif attempt_count == 2:
        return 10  # 第二次错误扣10分
    elif attempt_count == 3:
        return 15  # 第三次错误扣15分
    else:
        return 20  # 第四次及以上扣20分


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
        
        # 先检查用户是否存在以及是否被禁用
        try:
            user_check = User.objects.get(username=username)
            if not user_check.is_active:
                error = '该账户已被禁用，请联系管理员'
                return render(request, 'login.html', {'error': error})
        except User.DoesNotExist:
            pass  # 用户不存在，继续常规验证流程
        
        # 进行身份验证
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


def register_view(request):
    """用户注册视图 - 学生自主注册"""
    if request.user.is_authenticated:
        # 已登录用户直接跳转到首页
        return redirect('index')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        # 验证
        errors = []
        
        if not username:
            errors.append('用户名不能为空')
        elif len(username) < 3:
            errors.append('用户名至少需要3个字符')
        elif User.objects.filter(username=username).exists():
            errors.append('该用户名已被使用')
        
        if not password:
            errors.append('密码不能为空')
        elif len(password) < 6:
            errors.append('密码至少需要6个字符')
        
        if password != password2:
            errors.append('两次输入的密码不一致')
        
        if email and User.objects.filter(email=email).exists():
            errors.append('该邮箱已被使用')
        
        if errors:
            context = {
                'errors': errors,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
            return render(request, 'register.html', context)
        
        try:
            # 创建用户
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # 自动添加到学生组
            student_group, created = Group.objects.get_or_create(name='Students')
            user.groups.add(student_group)
            
            messages.success(request, f'注册成功！欢迎 {username}，请登录。')
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'注册失败：{str(e)}')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
    
    return render(request, 'register.html')


@login_required
def change_password_view(request):
    """修改密码视图"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        new_password2 = request.POST.get('new_password2', '')
        
        # 验证
        errors = []
        
        if not old_password:
            errors.append('请输入当前密码')
        elif not request.user.check_password(old_password):
            errors.append('当前密码不正确')
        
        if not new_password:
            errors.append('请输入新密码')
        elif len(new_password) < 6:
            errors.append('新密码至少需要6个字符')
        
        if new_password != new_password2:
            errors.append('两次输入的新密码不一致')
        
        if old_password == new_password:
            errors.append('新密码不能与当前密码相同')
        
        if errors:
            return render(request, 'change_password.html', {'errors': errors})
        
        try:
            # 修改密码
            request.user.set_password(new_password)
            request.user.save()
            
            # 更新session，避免用户被登出
            update_session_auth_hash(request, request.user)
            
            messages.success(request, '密码修改成功！')
            return redirect('index')
            
        except Exception as e:
            messages.error(request, f'密码修改失败：{str(e)}')
            return render(request, 'change_password.html')
    
    return render(request, 'change_password.html')


@login_required
def index(request):
    """首页 - 根据用户角色跳转"""
    if is_teacher(request.user):
        return redirect('teacher_dashboard')
    else:
        return redirect('student_dashboard')


# 学生端视图
def _format_minutes_as_hm(total_minutes: int) -> str:
    total_minutes = int(total_minutes or 0)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}min"
        return f"{hours}h"
    return f"{minutes}min"


def _parse_iso_dt(value):
    if not value:
        return None
    try:
        dt = timezone.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


def _get_user_total_study_time_minutes(user) -> int:
    """统一的学习时长口径（分钟），供教师端/学生端复用。"""
    user_sessions = StudentClinicalSession.objects.filter(student=user)
    completed_qs = user_sessions.filter(Q(session_status='completed') | Q(completed_at__isnull=False))

    total_study_time = 0
    for session in completed_qs:
        start_time = None
        try:
            sd = getattr(session, 'session_data', None) or {}
            start_time = _parse_iso_dt(sd.get('run_started_at'))
        except Exception:
            start_time = None

        if not start_time:
            start_time = getattr(session, 'started_at', None)
        if not start_time:
            continue

        completed_at = getattr(session, 'completed_at', None)
        last_activity = getattr(session, 'last_activity', None)
        end_time = None
        if completed_at and last_activity:
            end_time = max(completed_at, last_activity)
        else:
            end_time = completed_at or last_activity
        if not end_time:
            continue

        duration_seconds = (end_time - start_time).total_seconds()
        if duration_seconds <= 0:
            continue
        if duration_seconds > 24 * 60 * 60:
            continue

        total_study_time += (duration_seconds / 60)

    return int(round(total_study_time))


def _get_session_study_time_minutes(session) -> int | None:
    """单个会话（单病例）学习时长口径（分钟）。

    口径与总学习时长一致：start=run_started_at 优先，其次 started_at；
    end=max(completed_at,last_activity)；过滤非正值/超 24h 的异常数据。
    返回 None 表示无法计算。
    """
    if session is None:
        return None

    start_time = None
    try:
        sd = getattr(session, 'session_data', None) or {}
        start_time = _parse_iso_dt(sd.get('run_started_at'))
    except Exception:
        start_time = None

    if not start_time:
        start_time = getattr(session, 'started_at', None)
    if not start_time:
        return None

    completed_at = getattr(session, 'completed_at', None)
    last_activity = getattr(session, 'last_activity', None)
    if completed_at and last_activity:
        end_time = max(completed_at, last_activity)
    else:
        end_time = completed_at or last_activity
    if not end_time:
        return None

    duration_seconds = (end_time - start_time).total_seconds()
    if duration_seconds <= 0:
        return None
    if duration_seconds > 24 * 60 * 60:
        return None

    return int(round(duration_seconds / 60))


def _filter_timing_dict(raw_dict, run_start):
    """按本轮 run_started_at 过滤旧 timing（避免历史污染）。"""
    if not isinstance(raw_dict, dict) or not raw_dict:
        return raw_dict
    if not run_start:
        return raw_dict
    filtered = {}
    for k, v in raw_dict.items():
        dtv = _parse_iso_dt(v)
        if dtv is None or dtv >= run_start:
            filtered[str(k)] = v
    return filtered


def _build_review_payload_for_session(session) -> dict:
    """构造与学生端复盘字段一致的 review payload（教师端只读查看用）。"""
    if session is None:
        return {}

    session_data = getattr(session, 'session_data', None) or {}

    completed_at = getattr(session, 'completed_at', None)
    last_activity = getattr(session, 'last_activity', None)
    end_time = None
    try:
        candidates = [t for t in (completed_at, last_activity) if t is not None]
        if candidates:
            end_time = max(candidates)
    except Exception:
        end_time = completed_at or last_activity

    run_started_at = _parse_iso_dt(session_data.get('run_started_at'))
    if run_started_at is None:
        try:
            st = session_data.get('stage_times') or {}
            if isinstance(st, dict) and st:
                parsed = [_parse_iso_dt(v) for v in st.values()]
                parsed = [x for x in parsed if x is not None]
                if parsed:
                    run_started_at = min(parsed)
        except Exception:
            pass
    if run_started_at is None:
        run_started_at = getattr(session, 'started_at', None)

    session_total_ms = None
    if run_started_at and end_time and end_time >= run_started_at:
        try:
            session_total_ms = int((end_time - run_started_at).total_seconds() * 1000)
        except Exception:
            session_total_ms = None

    stage_times = _filter_timing_dict(session_data.get('stage_times'), run_started_at)
    stage_start_times = _filter_timing_dict(session_data.get('stage_start_times'), run_started_at)

    # 后端权威口径：各阶段用时（毫秒）
    stage_durations_ms = None
    try:
        end_time2 = end_time
        run_started_at2 = run_started_at
        if run_started_at2 is None:
            try:
                st2 = stage_times or {}
                if isinstance(st2, dict) and st2:
                    parsed2 = [_parse_iso_dt(v) for v in st2.values()]
                    parsed2 = [x for x in parsed2 if x is not None]
                    if parsed2:
                        run_started_at2 = min(parsed2)
            except Exception:
                pass
        if run_started_at2 is None:
            run_started_at2 = getattr(session, 'started_at', None)

        major_stages = ['case_presentation', 'examination_selection', 'diagnosis_reasoning', 'treatment_selection', 'learning_feedback']

        # 计算阶段开始
        stage_start_dt = {}
        sst = stage_start_times or {}
        if not isinstance(sst, dict):
            sst = {}

        inferred_to_stage = {}
        st = stage_times or {}
        if isinstance(st, dict):
            for k, v in st.items():
                m = re.match(r'^(.+)_to_(.+)$', str(k))
                if not m:
                    continue
                to_stage = m.group(2)
                dtv = _parse_iso_dt(v)
                if dtv is None:
                    continue
                if to_stage not in inferred_to_stage or dtv < inferred_to_stage[to_stage]:
                    inferred_to_stage[to_stage] = dtv

        for stg in major_stages:
            dtv = _parse_iso_dt(sst.get(stg)) or inferred_to_stage.get(stg)
            if dtv is None and stg == 'case_presentation':
                dtv = run_started_at2
            stage_start_dt[stg] = dtv

        # 计算阶段结束：开始之后最近的下一事件（其他阶段开始/会话结束）
        stage_end_dt = {}
        all_starts = [dt for dt in stage_start_dt.values() if dt is not None]
        for stg in major_stages:
            sdt = stage_start_dt.get(stg)
            if sdt is None:
                stage_end_dt[stg] = None
                continue
            candidates = [dt for dt in all_starts if dt > sdt]
            if end_time2 is not None and end_time2 > sdt:
                candidates.append(end_time2)
            stage_end_dt[stg] = min(candidates) if candidates else end_time2

        stage_durations_ms = {}
        for stg in major_stages:
            sdt = stage_start_dt.get(stg)
            edt = stage_end_dt.get(stg)
            if not sdt or not edt or edt < sdt:
                stage_durations_ms[stg] = None
                continue
            ms = int((edt - sdt).total_seconds() * 1000)
            if ms < 0 or ms > 24 * 60 * 60 * 1000:
                stage_durations_ms[stg] = None
            else:
                stage_durations_ms[stg] = ms
    except Exception:
        stage_durations_ms = None

    # 检查选择详情
    selected_exam_ids = []
    try:
        selected_exams_obj = getattr(session, 'selected_examinations', None)
        if isinstance(selected_exams_obj, list):
            selected_exam_ids = list(selected_exams_obj)
        else:
            selected_exam_ids = list(selected_exams_obj or [])
    except Exception:
        selected_exam_ids = []

    selected_exam_details = []
    if selected_exam_ids:
        try:
            exam_qs = ExaminationOption.objects.filter(id__in=selected_exam_ids)
            exam_by_id = {int(x.id): x for x in exam_qs}

            # 保持学生选择的顺序（JSON list 的顺序）
            ordered_ids = []
            for raw_id in selected_exam_ids:
                try:
                    ordered_ids.append(int(raw_id))
                except Exception:
                    continue

            selected_exam_details = []
            for exam_id in ordered_ids:
                obj = exam_by_id.get(int(exam_id))
                if not obj:
                    selected_exam_details.append({'id': int(exam_id), 'name': f'检查#{exam_id}'})
                    continue

                # 提取检查结果图片（与学生端展示结构兼容）
                images = []
                try:
                    # result_images: JSONField，可能是 string 或 dict
                    raw_imgs = getattr(obj, 'result_images', None) or []
                    if isinstance(raw_imgs, (list, tuple)):
                        for idx, it in enumerate(raw_imgs):
                            if isinstance(it, dict):
                                url = it.get('url') or it.get('path') or it.get('src')
                                if url:
                                    images.append({
                                        'url': url,
                                        'description': it.get('description') or f'结果图像 {idx + 1}',
                                    })
                            elif isinstance(it, str) and it.strip():
                                images.append({'url': it.strip(), 'description': f'结果图像 {idx + 1}'})

                    if getattr(obj, 'left_eye_image', None):
                        try:
                            images.append({'url': obj.left_eye_image.url, 'description': '左眼检查图片'})
                        except Exception:
                            pass
                    if getattr(obj, 'right_eye_image', None):
                        try:
                            images.append({'url': obj.right_eye_image.url, 'description': '右眼检查图片'})
                        except Exception:
                            pass

                    raw_additional = getattr(obj, 'additional_images', None) or []
                    if isinstance(raw_additional, (list, tuple)):
                        for idx, it in enumerate(raw_additional):
                            if isinstance(it, dict):
                                url = it.get('url') or it.get('path') or it.get('src')
                                if url:
                                    images.append({
                                        'url': url,
                                        'description': it.get('description') or f'附加图像 {idx + 1}',
                                    })
                            elif isinstance(it, str) and it.strip():
                                images.append({'url': it.strip(), 'description': f'附加图像 {idx + 1}'})
                except Exception:
                    images = []

                selected_exam_details.append(
                    {
                        'id': int(obj.id),
                        'name': getattr(obj, 'examination_name', '') or f'检查#{exam_id}',
                        'type': getattr(obj, 'examination_type', None),
                        'type_display': obj.get_examination_type_display() if hasattr(obj, 'get_examination_type_display') else getattr(obj, 'examination_type', ''),
                        'is_required': bool(getattr(obj, 'is_required', False)),
                        'is_recommended': bool(getattr(obj, 'is_recommended', False)),
                        'diagnostic_value': getattr(obj, 'diagnostic_value', None),
                        'cost_effectiveness': getattr(obj, 'cost_effectiveness', None),
                        'description': getattr(obj, 'examination_description', '') or '',
                        'actual_result': getattr(obj, 'actual_result', '') or '',
                        'images': images,
                    }
                )
        except Exception:
            selected_exam_details = [{'id': int(exam_id), 'name': f'检查#{exam_id}'} for exam_id in selected_exam_ids]

    diagnosis_record = session_data.get('diagnosis')
    treatment_record = session_data.get('treatment')

    # 治疗选择详情
    selected_treatment_ids = []
    try:
        if isinstance(treatment_record, dict) and treatment_record.get('treatment_ids'):
            selected_treatment_ids = list(treatment_record.get('treatment_ids') or [])
        else:
            selected_treats_obj = getattr(session, 'selected_treatments', None)
            if isinstance(selected_treats_obj, list):
                selected_treatment_ids = list(selected_treats_obj)
            else:
                selected_treatment_ids = list(selected_treats_obj or [])
    except Exception:
        selected_treatment_ids = []

    selected_treatment_details = []
    if selected_treatment_ids:
        try:
            rows = list(TreatmentOption.objects.filter(id__in=selected_treatment_ids).values('id', 'treatment_name'))
            id_to_name = {row['id']: row.get('treatment_name') for row in rows}
            selected_treatment_details = [
                {'id': int(tid), 'name': id_to_name.get(int(tid)) or f'治疗#{tid}'}
                for tid in selected_treatment_ids
            ]
        except Exception:
            selected_treatment_details = [{'id': int(tid), 'name': f'治疗#{tid}'} for tid in selected_treatment_ids]

    return {
        'selected_examinations': selected_exam_details,
        'diagnosis': diagnosis_record,
        'selected_treatments': selected_treatment_details,
        'treatment': treatment_record,
        'stage_times': stage_times,
        'stage_start_times': stage_start_times,
        'stage_durations_ms': stage_durations_ms,
        'session_started_at': run_started_at.isoformat() if run_started_at else None,
        'session_completed_at': completed_at.isoformat() if completed_at else None,
        'session_last_activity_at': last_activity.isoformat() if last_activity else None,
        'session_total_ms': session_total_ms,
    }


def _get_student_clinical_stats(user):
    """统一的学生端临床推理统计口径（dashboard 与 API 共用）"""
    total_cases = ClinicalCase.objects.filter(is_active=True).count()
    user_sessions = StudentClinicalSession.objects.filter(student=user)

    completed_qs = user_sessions.filter(Q(session_status='completed') | Q(completed_at__isnull=False))
    completed_cases = completed_qs.count()

    progress_percentage = 0
    if total_cases > 0:
        progress_percentage = round((completed_cases / total_cases) * 100, 1)

    # 平均分：只统计有有效得分的记录；优先使用已完成会话
    avg_overall = (
        completed_qs.filter(overall_score__gt=0)
        .aggregate(Avg('overall_score'))
        .get('overall_score__avg')
        or 0
    )

    # 总学习时长（分钟）：使用“本轮学习起点 run_started_at”避免老会话 created_at/started_at 导致爆炸
    total_study_time = _get_user_total_study_time_minutes(user)

    stats = {
        'total_cases': total_cases,
        'completed_cases': completed_cases,
        'progress_percentage': progress_percentage,
        'total_study_time': total_study_time,
        'formatted_study_time': _format_minutes_as_hm(total_study_time),
        'average_score': round(avg_overall, 2),
        'difficulty_progress': {
            'beginner': {
                'completed': completed_qs.filter(clinical_case__difficulty_level='beginner').count(),
                'total': ClinicalCase.objects.filter(difficulty_level='beginner', is_active=True).count(),
            },
            'intermediate': {
                'completed': completed_qs.filter(clinical_case__difficulty_level='intermediate').count(),
                'total': ClinicalCase.objects.filter(difficulty_level='intermediate', is_active=True).count(),
            },
            'advanced': {
                'completed': completed_qs.filter(clinical_case__difficulty_level='advanced').count(),
                'total': ClinicalCase.objects.filter(difficulty_level='advanced', is_active=True).count(),
            },
        },
    }
    return stats


@login_required
@user_passes_test(is_student, login_url='login')
def student_dashboard(request):
    """学生仪表板"""
    user = request.user

    stats = _get_student_clinical_stats(user)
    total_clinical_cases = stats.get('total_cases', 0)
    completed_sessions = stats.get('completed_cases', 0)

    # 最近学习记录
    recent_sessions = StudentClinicalSession.objects.filter(student=user).order_by('-started_at')[:5]

    # 模拟进度对象结构
    progress = {
        'progress_percentage': stats.get('progress_percentage', 0),
        'total_study_time': stats.get('total_study_time', 0),
        'formatted_study_time': stats.get('formatted_study_time', '0min'),
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
    
    # 为每个会话计算学习时长（与学生端统计口径对齐：run_started_at 作为本轮起点，过滤历史脏数据）
    sessions_with_time = []
    cached_user_total_minutes = {}
    for session in recent_sessions:
        student_id = getattr(session.student, 'id', None)
        if student_id not in cached_user_total_minutes:
            cached_user_total_minutes[student_id] = _get_user_total_study_time_minutes(session.student)

        total_minutes = cached_user_total_minutes[student_id]
        formatted_time = _format_minutes_as_hm(total_minutes)

        case_minutes = _get_session_study_time_minutes(session)
        formatted_case_time = _format_minutes_as_hm(case_minutes) if isinstance(case_minutes, int) else '-'

        sessions_with_time.append(
            {
                'session': session,
                'total_study_time': formatted_time,
                'case_study_time': formatted_case_time,
            }
        )
    
    context = {
        'total_clinical_cases': total_clinical_cases,
        'active_clinical_cases': active_clinical_cases,
        'total_students': total_students,
        'total_examinations': total_examinations,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'completion_rate': completion_rate,
        'recent_sessions': sessions_with_time,
    }
    
    return render(request, 'teacher/dashboard.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_session_review(request, session_id: int):
    """教师端：查看某个学生在某个病例的学习反馈（只读复盘）。"""
    session = get_object_or_404(
        StudentClinicalSession.objects.select_related('student', 'clinical_case'),
        id=session_id,
    )
    review = _build_review_payload_for_session(session)

    total_minutes = None
    try:
        total_ms = review.get('session_total_ms')
        if isinstance(total_ms, int) and total_ms >= 0:
            total_minutes = int(round(total_ms / 60000))
    except Exception:
        total_minutes = None

    stage_minutes = {}
    try:
        sdm = review.get('stage_durations_ms')
        if isinstance(sdm, dict):
            for k, v in sdm.items():
                if isinstance(v, int) and v >= 0:
                    stage_minutes[str(k)] = int(round(v / 60000))
                else:
                    stage_minutes[str(k)] = None
    except Exception:
        stage_minutes = {}

    context = {
        'session': session,
        'review': review,
        'total_study_time': _format_minutes_as_hm(total_minutes) if isinstance(total_minutes, int) else '-',
        'stage_minutes': stage_minutes,
    }
    return render(request, 'teacher/session_review.html', context)


































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
            defaults={'session_status': 'case_presentation'}
        )
        
        # 如果是新会话，重置状态
        if created:
            session.session_status = 'case_presentation'
            session.save()
        else:
            # 如果是已完成的会话，重置为新的学习会话（保留历史记录但重置计数）
            if session.session_status == 'completed' or session.completed_at is not None:
                # 重置会话状态，开始新一轮学习
                session.session_status = 'case_presentation'
                session.completed_at = None
                # 重置本轮计时，避免继承历史 started_at / stage_times
                session.started_at = timezone.now()
                session.time_spent = {}
                session.step_start_times = {}
                session.session_data = {}
                # 重置尝试次数和指导级别，避免"终生惩罚"
                session.diagnosis_attempt_count = 0
                session.diagnosis_guidance_level = 0
                # 重置分数（但保留历史最高分在其他字段中）
                session.examination_score = 0
                session.diagnosis_score = 0
                session.treatment_score = 0
                session.overall_score = 0
                # 清空当前选择
                session.selected_examinations.clear()
                session.selected_diagnoses = []
                session.selected_treatments = []
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
            defaults={'session_status': 'case_presentation'}
        )
        
        # 如果是新会话，重置状态
        if created:
            session.session_status = 'case_presentation'
            session.save()
        else:
            # 如果是已完成的会话，重置为新的学习会话（保留历史记录但重置计数）
            if session.session_status == 'completed' or session.completed_at is not None:
                # 重置会话状态，开始新一轮学习
                session.session_status = 'case_presentation'
                session.completed_at = None
                # 重置尝试次数和指导级别，避免"终生惩罚"
                session.diagnosis_attempt_count = 0
                session.diagnosis_guidance_level = 0
                # 重置分数（但保留历史最高分在其他字段中）
                session.examination_score = 0
                session.diagnosis_score = 0
                session.treatment_score = 0
                session.overall_score = 0
                # 清空当前选择
                session.selected_examinations.clear()
                session.selected_diagnoses = []
                session.selected_treatments = []
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
def save_clinical_notes(request):
    """保存临床笔记到数据库"""
    try:
        data = json.loads(request.body)
        case_id = data.get('case_id')
        notes = data.get('notes', '')
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        session = get_object_or_404(StudentClinicalSession, 
                                  student=request.user, 
                                  clinical_case=clinical_case)
        
        # 保存笔记到数据库
        session.learning_notes = notes
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '笔记已保存',
            'data': {
                'notes_length': len(notes),
                'save_time': timezone.now().strftime('%H:%M:%S')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'保存笔记失败：{str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_student, login_url='login')
def get_clinical_notes(request, case_id):
    """获取临床笔记"""
    try:
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        session = get_object_or_404(StudentClinicalSession, 
                                  student=request.user, 
                                  clinical_case=clinical_case)
        
        return JsonResponse({
            'success': True,
            'data': {
                'notes': session.learning_notes or '',
                'last_updated': session.last_activity.strftime('%Y-%m-%d %H:%M:%S') if session.learning_notes else None
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取笔记失败：{str(e)}'
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
        session.session_status = 'diagnosis_reasoning'
        
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
        selected_diagnosis_ids = data.get('selected_diagnosis_ids', [])  # 支持多个诊断
        selected_diagnosis_id = data.get('selected_diagnosis_id')  # 兼容旧的单诊断
        reasoning = data.get('reasoning', '')
        
        # 兼容处理：如果使用旧的单诊断格式，转换为数组
        if selected_diagnosis_id and not selected_diagnosis_ids:
            selected_diagnosis_ids = [selected_diagnosis_id]
        
        if not selected_diagnosis_ids:
            return JsonResponse({
                'success': False,
                'message': '请至少选择一个诊断选项'
            }, status=400)
        
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id, is_active=True)
        session = get_object_or_404(StudentClinicalSession, 
                                  student=request.user, 
                                  clinical_case=clinical_case)
        
        # 验证所有选择的诊断都属于该案例
        diagnosis_options = DiagnosisOption.objects.filter(
            id__in=selected_diagnosis_ids, 
            clinical_case=clinical_case
        )
        
        if len(diagnosis_options) != len(selected_diagnosis_ids):
            return JsonResponse({
                'success': False,
                'message': '选择的诊断选项无效'
            }, status=400)
        
        # 获取所有正确诊断以供比较
        all_correct_diagnoses = DiagnosisOption.objects.filter(
            clinical_case=clinical_case, 
            is_correct_diagnosis=True
        )
        correct_diagnosis_ids = set(all_correct_diagnoses.values_list('id', flat=True))
        selected_diagnosis_ids_set = set(selected_diagnosis_ids)
        
        # 计算诊断结果
        correct_diagnoses = diagnosis_options.filter(is_correct_diagnosis=True)
        total_selected = len(diagnosis_options)
        correct_selected = len(correct_diagnoses)
        
        # 检查是否完全正确
        is_completely_correct = (selected_diagnosis_ids_set == correct_diagnosis_ids)
        
        # 增加尝试次数
        session.diagnosis_attempt_count += 1

        # 持久化“诊断选择 + 诊断依据”，用于学习反馈复盘（刷新不丢）
        if not getattr(session, 'session_data', None):
            session.session_data = {}
        try:
            session.session_data['diagnosis'] = {
                'diagnosis_ids': list(selected_diagnosis_ids),
                'diagnosis_names': [opt.diagnosis_name for opt in diagnosis_options],
                'diagnosis_rationale': reasoning,
                'attempt_count': session.diagnosis_attempt_count,
            }
        except Exception:
            session.session_data['diagnosis'] = {
                'diagnosis_ids': list(selected_diagnosis_ids),
                'diagnosis_names': [],
                'diagnosis_rationale': reasoning,
                'attempt_count': session.diagnosis_attempt_count,
            }
        
        if is_completely_correct:
            # 诊断完全正确 - 进入治疗阶段
            session.selected_diagnoses = selected_diagnosis_ids
            session.session_status = 'treatment_selection'
            # 修复：使用当前尝试次数计算分数（第1次=100分，第2次=90分，以此类推，最低60分）
            session.diagnosis_score = max(100 - (session.diagnosis_attempt_count - 1) * 10, 60)  # 最低60分
            
            feedback_message = f"恭喜！您的鉴别诊断完全正确！"
            if session.diagnosis_attempt_count > 1:
                feedback_message += f"（第{session.diagnosis_attempt_count}次尝试，得分：{session.diagnosis_score:.0f}分）"
            else:
                feedback_message += f"（首次尝试即正确，满分100分！）"
            feedback_type = 'positive'
            
        elif correct_selected > 0:
            # 部分正确 - 提供指导并允许重新选择
            wrong_selected = total_selected - correct_selected
            missing_correct = len(correct_diagnosis_ids) - len(selected_diagnosis_ids_set & correct_diagnosis_ids)
            
            # 根据尝试次数提供不同级别的指导
            if session.diagnosis_attempt_count == 1:
                session.diagnosis_guidance_level = 1
                guidance_hint = f"您选择了{correct_selected}个正确诊断，但还有{missing_correct}个正确诊断未选择"
                if wrong_selected > 0:
                    guidance_hint += f"，同时选择了{wrong_selected}个错误诊断"
                guidance_hint += "。请重新思考并调整您的选择。"
                
            elif session.diagnosis_attempt_count == 2:
                session.diagnosis_guidance_level = 2
                guidance_hint = "提示：请仔细回顾患者的症状、体征和检查结果。"
                # 给出轻度提示
                wrong_options = diagnosis_options.filter(is_correct_diagnosis=False)
                if wrong_options.exists():
                    for option in wrong_options:
                        if option.hint_level_1:
                            guidance_hint += f"\n关于{option.diagnosis_name}: {option.hint_level_1}"
                            
            elif session.diagnosis_attempt_count == 3:
                session.diagnosis_guidance_level = 3  
                guidance_hint = "进一步提示："
                # 给出中度提示
                wrong_options = diagnosis_options.filter(is_correct_diagnosis=False)
                if wrong_options.exists():
                    for option in wrong_options:
                        if option.hint_level_2:
                            guidance_hint += f"\n{option.diagnosis_name}: {option.hint_level_2}"
                            
            else:  # 第4次及以上
                session.diagnosis_guidance_level = 3
                guidance_hint = "详细指导："
                # 给出强提示
                all_diagnosis_options = DiagnosisOption.objects.filter(clinical_case=clinical_case)
                for option in all_diagnosis_options:
                    if option.is_correct_diagnosis:
                        guidance_hint += f"\n✓ {option.diagnosis_name}: 这是正确的诊断"
                    else:
                        if option.hint_level_3:
                            guidance_hint += f"\n✗ {option.diagnosis_name}: {option.hint_level_3}"
            
            feedback_message = guidance_hint
            feedback_type = 'guidance'
            session.diagnosis_score = 0  # 未完成时不给分
            # 不改变session_status，允许重新选择
            
        else:
            # 完全错误 - 提供基础指导
            session.diagnosis_guidance_level = min(session.diagnosis_attempt_count, 3)
            
            if session.diagnosis_attempt_count == 1:
                feedback_message = f"您选择的{total_selected}个诊断都不正确。请重新分析患者的症状、体征和检查结果，考虑可能的鉴别诊断。\n\n💡 提示：仔细观察患者的检查结果和临床表现。"
            elif session.diagnosis_attempt_count == 2:
                feedback_message = "请注意以下诊断要点："
                # 给出正确诊断的轻度提示
                for correct_diagnosis in all_correct_diagnoses:
                    if correct_diagnosis.hint_level_1:
                        feedback_message += f"\n• {correct_diagnosis.diagnosis_name}: {correct_diagnosis.hint_level_1}"
            else:
                feedback_message = "详细指导 - 请考虑以下正确诊断："
                # 给出正确诊断的详细提示
                for correct_diagnosis in all_correct_diagnoses:
                    feedback_message += f"\n✓ {correct_diagnosis.diagnosis_name}: "
                    if correct_diagnosis.hint_level_2:
                        feedback_message += correct_diagnosis.hint_level_2
                    else:
                        feedback_message += "这是正确的鉴别诊断选项"
                        
            feedback_type = 'corrective'
            session.diagnosis_score = 0
        
        session.save()
        
        # 创建诊断阶段反馈
        TeachingFeedback.objects.create(
            student_session=session,
            feedback_stage='diagnosis',
            feedback_type=feedback_type,
            feedback_content=feedback_message,
            is_automated=True
        )
        
        # 准备返回数据
        response_data = {
            'diagnosis_feedback': feedback_message,
            'diagnosis_score': session.diagnosis_score,
            'attempt_count': session.diagnosis_attempt_count,
            'guidance_level': session.diagnosis_guidance_level,
            'current_stage': session.session_status,
        }
        
        # 如果诊断完全正确，准备治疗选项
        if is_completely_correct:
            # 获取相关的治疗选项 - 基于选择的诊断
            treatment_options = TreatmentOption.objects.filter(
                clinical_case=clinical_case,
                related_diagnosis__in=diagnosis_options
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
            
            response_data.update({
                'treatment_options': treatment_data,
                'next_stage': 'treatment',
                'message': '诊断选择正确，请选择治疗方案'
            })
        else:
            # 诊断不完全正确，返回诊断选项供重新选择
            all_diagnosis_options = DiagnosisOption.objects.filter(
                clinical_case=clinical_case
            ).order_by('display_order')
            
            diagnosis_data = [{
                'id': option.id,
                'name': option.diagnosis_name,
                'code': option.diagnosis_code,
                'is_differential': option.is_differential,
                'probability_score': option.probability_score,
                'is_correct': option.is_correct_diagnosis  # 在指导模式下可以显示
            } for option in all_diagnosis_options]
            
            response_data.update({
                'diagnosis_options': diagnosis_data,
                'next_stage': 'diagnosis',
                'allow_retry': True,
                'message': '请根据指导重新选择鉴别诊断'
            })
        
        # 准备选中诊断的信息（用于显示）
        selected_diagnoses_data = [{
            'id': d.id,
            'name': d.diagnosis_name,
            'code': d.diagnosis_code,
            'is_correct': d.is_correct_diagnosis
        } for d in diagnosis_options]
        response_data['selected_diagnoses'] = selected_diagnoses_data
        
        return JsonResponse({
            'success': True,
            'data': response_data
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
        # 获取必选项名称集合，用于去重
        required_exam_names = set(exam.examination_name for exam in required_examinations)
        
        # 获取其他案例的检查项目作为干扰项池
        distractor_pool = ExaminationOption.objects.exclude(
            clinical_case=clinical_case
        )
        
        # 如果干扰项池不够，使用当前案例的可选项作为补充
        if distractor_pool.count() < 3:
            # 从当前案例的可选项中排除与必选项同名的选项
            distractor_pool = optional_examinations.exclude(
                examination_name__in=required_exam_names
            )
        
        # 去重：移除与必选项同名的干扰项，避免重复
        unique_distractors = []
        seen_names = set(required_exam_names)  # 初始化已见过的名称集合
        
        for exam in distractor_pool:
            if exam.examination_name not in seen_names:
                unique_distractors.append(exam)
                seen_names.add(exam.examination_name)
        
        # 按检查类型分组，确保干扰项类型多样性
        distractor_by_type = {}
        for exam in unique_distractors:
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
        
        # 如果还需要更多干扰项，从去重后的池中随机选择剩余的
        if len(selected_distractors) < distractor_count:
            remaining_pool = [exam for exam in unique_distractors 
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
        
        # 在列表开头插入"体格检查"选项
        physical_exam_option = {
            'id': 'physical_exam',  # 特殊ID标识
            'type': '基础检查',
            'name': '体格检查',
            'description': '包括视力、眼压、外眼检查、瞳孔检查、结膜检查、角膜检查等基础体格检查项目',
            'diagnostic_value': '基础必要',
            'cost_effectiveness': '高性价比',
            'is_recommended': True,
            'is_required': True,
            'is_multiple_choice': False,
            'images': [],
            'is_case_required': True,
            'is_distractor': False,
            'is_physical_exam': True  # 特殊标识
        }
        options_data.insert(0, physical_exam_option)
        
        # 验证去重效果：检查是否有重复名称
        all_names = [option.examination_name for option in all_examinations]
        unique_names = set(all_names)
        
        return JsonResponse({
            'success': True,
            'data': {
                'examination_options': options_data,
                'total_count': len(options_data),
                'required_count': required_count,
                'distractor_count': len(selected_distractors),
                'unique_names_count': len(unique_names),  # 调试：实际去重后的唯一名称数量
                'mode': 'mixed'  # 混合模式，包含必选项和干扰项
            },
            'message': f'检查选项获取成功（含{required_count}个必选项和{len(selected_distractors)}个去重干扰项）'
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
        
        # 尝试获取检查选项（可能是本病例的，也可能是干扰项）
        try:
            examination = ExaminationOption.objects.get(id=exam_id)
        except ExaminationOption.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '检查选项不存在'
            }, status=404)
        
        # 判断是否为干扰项（不属于当前病例）
        is_distractor = examination.clinical_case_id != clinical_case.id
        
        if is_distractor:
            # 干扰项：返回"无相关检查信息"
            return JsonResponse({
                'success': False,
                'result': {
                    'id': examination.id,
                    'name': examination.examination_name,
                    'type': examination.get_examination_type_display(),
                    'actual_result': '无相关检查信息',
                    'is_relevant': False
                },
                'message': '该检查对本病例无诊断价值'
            })
        
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
        
        # 验证选择的检查项目是否存在（包括来自其他案例的干扰项）
        examination_options = ExaminationOption.objects.filter(
            id__in=selected_examinations  # 移除 clinical_case 限制，允许干扰项
        )
        
        if len(examination_options) != len(selected_examinations):
            # 提供更详细的错误信息，帮助调试
            found_ids = set(examination_options.values_list('id', flat=True))
            missing_ids = set(selected_examinations) - found_ids
            return JsonResponse({
                'success': False,
                'message': f'选择的检查项目不存在，缺失ID: {list(missing_ids)}'
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
        try:
            import traceback
            print('[clinical_cases_list] error:', str(e))
            print(traceback.format_exc())
        except Exception:
            pass
        # 前端会根据 success 字段提示，不要用 500 让浏览器报 Failed to load resource
        return JsonResponse({'success': False, 'message': str(e), 'data': {'cases': []}}, status=200)


@login_required
@user_passes_test(is_student, login_url='login')
def clinical_user_stats(request):
    """返回当前学生的临床学习统计数据"""
    try:
        stats = _get_student_clinical_stats(request.user)
        return JsonResponse({'success': True, 'data': stats})
    except Exception as e:
        try:
            import traceback
            print('[clinical_user_stats] error:', str(e))
            print(traceback.format_exc())
        except Exception:
            pass
        fallback = {
            'total_cases': 0,
            'completed_cases': 0,
            'progress_percentage': 0,
            'total_study_time': 0,
            'formatted_study_time': '0min',
            'average_score': 0,
            'difficulty_progress': {
                'beginner': {'completed': 0, 'total': 0},
                'intermediate': {'completed': 0, 'total': 0},
                'advanced': {'completed': 0, 'total': 0},
            },
        }
        return JsonResponse({'success': False, 'message': str(e), 'data': fallback}, status=200)


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

            # 复盘所需数据：检查选择、诊断提交、阶段用时等（即使部分字段异常，也不要让接口500）
            review_payload = {
                'selected_examinations': [],
                'diagnosis': None,
                'selected_treatments': [],
                'treatment': None,
                'stage_times': None,
                'stage_start_times': None,
                'session_started_at': None,
                'session_completed_at': None,
                'session_last_activity_at': None,
                'session_total_ms': None,
            }
            try:
                session_data = getattr(session, 'session_data', None) or {}

                # 可选：后端计时 debug 输出（只在开发模式开启，避免泄露/干扰生产）
                debug_time_enabled = bool(getattr(settings, 'DEBUG', False)) and (request.GET.get('debug_time') in ('1', 'true', 'True'))
                debug_time = None

                # 会话时间（用于前端校准总用时与阶段用时）
                try:
                    # 注意：StudentClinicalSession.started_at 是 auto_now_add（会话创建时间），
                    # 不能作为“本轮学习开始时间”，否则旧会话会导致总用时异常变大。
                    completed_at = getattr(session, 'completed_at', None)
                    last_activity = getattr(session, 'last_activity', None)
                    review_payload['session_completed_at'] = completed_at.isoformat() if completed_at else None
                    review_payload['session_last_activity_at'] = last_activity.isoformat() if last_activity else None

                    def _parse_dt(value):
                        if not value:
                            return None
                        try:
                            dt = timezone.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                            if timezone.is_naive(dt):
                                dt = timezone.make_aware(dt, timezone.get_current_timezone())
                            return dt
                        except Exception:
                            return None

                    run_started_at = _parse_dt(session_data.get('run_started_at'))

                    # 兜底：若没有 run_started_at，用 stage_times 的最早时间戳作为“本轮起点”
                    if run_started_at is None:
                        try:
                            st = session_data.get('stage_times') or {}
                            if isinstance(st, dict) and st:
                                parsed = [_parse_dt(v) for v in st.values()]
                                parsed = [x for x in parsed if x is not None]
                                if parsed:
                                    run_started_at = min(parsed)
                        except Exception:
                            pass

                    # 最后兜底：使用会话创建时间（可能偏旧，但至少有值）
                    if run_started_at is None:
                        started_at = getattr(session, 'started_at', None)
                        run_started_at = started_at

                    review_payload['session_started_at'] = run_started_at.isoformat() if run_started_at else None

                    # 结束时间：优先取“更晚”的那个，避免 completed_at < last_activity 造成用时/阶段结束时间倒挂
                    end_time = None
                    try:
                        candidates = [t for t in (completed_at, last_activity) if t is not None]
                        if candidates:
                            end_time = max(candidates)
                    except Exception:
                        end_time = completed_at or last_activity
                    if run_started_at and end_time and end_time >= run_started_at:
                        review_payload['session_total_ms'] = int((end_time - run_started_at).total_seconds() * 1000)

                    # 组织 debug_time（不影响正常逻辑）
                    if debug_time_enabled:
                        try:
                            major_stages = ['case_presentation', 'examination_selection', 'diagnosis_reasoning', 'treatment_selection', 'learning_feedback']

                            raw_stage_start_times = session_data.get('stage_start_times') if isinstance(session_data.get('stage_start_times'), dict) else {}
                            raw_stage_times = session_data.get('stage_times') if isinstance(session_data.get('stage_times'), dict) else {}

                            parsed_stage_start_times = {}
                            for k, v in (raw_stage_start_times or {}).items():
                                parsed_stage_start_times[str(k)] = _parse_dt(v)

                            # 按本轮 run_started_at 过滤旧的 stage_times（避免历史污染导致“阶段顺序倒挂”）
                            filtered_stage_times = {}
                            if isinstance(raw_stage_times, dict) and raw_stage_times:
                                for key, val in raw_stage_times.items():
                                    dtv = _parse_dt(val)
                                    if dtv is None:
                                        continue
                                    if run_started_at and dtv < run_started_at:
                                        continue
                                    filtered_stage_times[str(key)] = val

                            # 由 stage_times 反推进入某阶段的时间（key: old_to_new）
                            inferred_to_stage_times = {}
                            for key, val in (filtered_stage_times or {}).items():
                                m = re.match(r'^(.+)_to_(.+)$', str(key))
                                if not m:
                                    continue
                                to_stage = m.group(2)
                                dtv = _parse_dt(val)
                                if dtv is not None:
                                    # 同一 to_stage 可能多次出现，取最早一次作为“首次进入”
                                    if to_stage not in inferred_to_stage_times or dtv < inferred_to_stage_times[to_stage]:
                                        inferred_to_stage_times[to_stage] = dtv

                            # 计算每个主阶段的开始时间：优先 stage_start_times，其次 stage_times 推断，其次 run_started_at（仅用于 case_presentation）
                            stage_start_dt = {}
                            for stg in major_stages:
                                dtv = parsed_stage_start_times.get(stg) or inferred_to_stage_times.get(stg)
                                if dtv is None and stg == 'case_presentation':
                                    dtv = run_started_at
                                stage_start_dt[stg] = dtv

                            # 计算结束时间：不再依赖固定阶段顺序；
                            # 而是为每个阶段选择“开始时间之后最近发生的下一事件（其他阶段开始/会话结束）”。
                            stage_end_dt = {}
                            all_starts = [dt for dt in stage_start_dt.values() if dt is not None]
                            for stg in major_stages:
                                sdt = stage_start_dt.get(stg)
                                if sdt is None:
                                    stage_end_dt[stg] = None
                                    continue
                                candidates = []
                                for dt in all_starts:
                                    if dt > sdt:
                                        candidates.append(dt)
                                if end_time is not None and end_time > sdt:
                                    candidates.append(end_time)
                                stage_end_dt[stg] = min(candidates) if candidates else end_time

                            stage_durations_ms = {}
                            stage_anomalies = {}
                            total_ms = review_payload.get('session_total_ms')
                            for stg in major_stages:
                                sdt = stage_start_dt.get(stg)
                                edt = stage_end_dt.get(stg)
                                if not sdt or not edt:
                                    stage_durations_ms[stg] = None
                                    stage_anomalies[stg] = 'missing_start_or_end'
                                    continue
                                if edt < sdt:
                                    stage_durations_ms[stg] = None
                                    stage_anomalies[stg] = 'end_before_start'
                                    continue
                                ms = int((edt - sdt).total_seconds() * 1000)
                                # 极端异常：超过 24h 直接标记
                                if ms > 24 * 60 * 60 * 1000:
                                    stage_durations_ms[stg] = ms
                                    stage_anomalies[stg] = 'duration_gt_24h'
                                else:
                                    stage_durations_ms[stg] = ms

                                # 合理性校验：阶段用时不应远大于总用时（允许 30s 误差）
                                if isinstance(total_ms, int) and total_ms >= 0 and ms > total_ms + 30_000:
                                    stage_anomalies[stg] = (stage_anomalies.get(stg) or '') + '|duration_gt_total'

                            debug_time = {
                                'tz': {
                                    'USE_TZ': bool(getattr(settings, 'USE_TZ', False)),
                                    'TIME_ZONE': str(getattr(settings, 'TIME_ZONE', '')),
                                    'now_iso': timezone.now().isoformat(),
                                },
                                'session_fields': {
                                    'session_status': getattr(session, 'session_status', None),
                                    'started_at': getattr(session, 'started_at', None).isoformat() if getattr(session, 'started_at', None) else None,
                                    'completed_at': completed_at.isoformat() if completed_at else None,
                                    'last_activity': last_activity.isoformat() if last_activity else None,
                                },
                                'run_started_at': {
                                    'raw': session_data.get('run_started_at'),
                                    'parsed': run_started_at.isoformat() if run_started_at else None,
                                },
                                'stage_start_times': {
                                    'raw': raw_stage_start_times,
                                    'parsed': {k: (v.isoformat() if v else None) for k, v in parsed_stage_start_times.items()},
                                },
                                'stage_times': {
                                    'raw': raw_stage_times,
                                    'inferred_to_stage_first_enter': {k: (v.isoformat() if v else None) for k, v in inferred_to_stage_times.items()},
                                },
                                'derived': {
                                    'end_time_used': end_time.isoformat() if end_time else None,
                                    'session_total_ms': review_payload.get('session_total_ms'),
                                    'stage_start_dt': {k: (v.isoformat() if v else None) for k, v in stage_start_dt.items()},
                                    'stage_end_dt': {k: (v.isoformat() if v else None) for k, v in stage_end_dt.items()},
                                    'stage_durations_ms': stage_durations_ms,
                                    'stage_anomalies': stage_anomalies,
                                },
                            }
                        except Exception:
                            debug_time = {'error': 'debug_time_build_failed'}
                except Exception:
                    pass

                # selected_examinations 可能是 list(JSONField) 或 M2M manager，做兼容读取
                selected_exam_ids = []
                try:
                    selected_exams_obj = getattr(session, 'selected_examinations', None)
                    if hasattr(selected_exams_obj, 'values_list'):
                        selected_exam_ids = list(selected_exams_obj.values_list('id', flat=True))
                    else:
                        selected_exam_ids = list(selected_exams_obj or [])
                except Exception:
                    selected_exam_ids = []

                selected_exam_details = []
                if selected_exam_ids:
                    try:
                        from cases.models import ExaminationOption
                        exam_rows = list(ExaminationOption.objects.filter(id__in=selected_exam_ids).values('id', 'examination_name'))
                        id_to_name = {row['id']: row.get('examination_name') for row in exam_rows}
                        selected_exam_details = [
                            {'id': int(exam_id), 'name': id_to_name.get(int(exam_id)) or f'检查#{exam_id}'}
                            for exam_id in selected_exam_ids
                        ]
                    except Exception:
                        selected_exam_details = [{'id': int(exam_id), 'name': f'检查#{exam_id}'} for exam_id in selected_exam_ids]

                diagnosis_record = session_data.get('diagnosis')
                treatment_record = session_data.get('treatment')

                # 仅返回“本轮”计时数据，避免旧 run 的 stage_times 混入导致前端复盘/调试紊乱
                def _filter_timing_dict(raw_dict, run_start):
                    if not isinstance(raw_dict, dict) or not raw_dict:
                        return raw_dict
                    if not run_start:
                        return raw_dict
                    filtered = {}
                    for k, v in raw_dict.items():
                        dtv = None
                        try:
                            dtv = timezone.datetime.fromisoformat(str(v).replace('Z', '+00:00'))
                            if timezone.is_naive(dtv):
                                dtv = timezone.make_aware(dtv, timezone.get_current_timezone())
                        except Exception:
                            dtv = None
                        if dtv is None or dtv >= run_start:
                            filtered[str(k)] = v
                    return filtered

                run_started_at = None
                try:
                    run_started_at = timezone.datetime.fromisoformat(str(session_data.get('run_started_at')).replace('Z', '+00:00')) if session_data.get('run_started_at') else None
                    if run_started_at and timezone.is_naive(run_started_at):
                        run_started_at = timezone.make_aware(run_started_at, timezone.get_current_timezone())
                except Exception:
                    run_started_at = None

                stage_times = _filter_timing_dict(session_data.get('stage_times'), run_started_at)
                stage_start_times = _filter_timing_dict(session_data.get('stage_start_times'), run_started_at)

                # 后端权威口径：计算各主阶段用时（毫秒），前端不再兜底/估算。
                stage_durations_ms = None
                try:
                    def _parse_dt2(value):
                        if not value:
                            return None
                        try:
                            dt = timezone.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                            if timezone.is_naive(dt):
                                dt = timezone.make_aware(dt, timezone.get_current_timezone())
                            return dt
                        except Exception:
                            return None

                    completed_at2 = getattr(session, 'completed_at', None)
                    last_activity2 = getattr(session, 'last_activity', None)
                    end_time2 = None
                    try:
                        candidates2 = [t for t in (completed_at2, last_activity2) if t is not None]
                        if candidates2:
                            end_time2 = max(candidates2)
                    except Exception:
                        end_time2 = completed_at2 or last_activity2

                    # run_started_at 再兜底一次：若缺失，用本轮 stage_times 最早时间戳；最后才回退 started_at
                    run_started_at2 = run_started_at
                    if run_started_at2 is None:
                        try:
                            st2 = stage_times or {}
                            if isinstance(st2, dict) and st2:
                                parsed2 = [_parse_dt2(v) for v in st2.values()]
                                parsed2 = [x for x in parsed2 if x is not None]
                                if parsed2:
                                    run_started_at2 = min(parsed2)
                        except Exception:
                            pass
                    if run_started_at2 is None:
                        run_started_at2 = getattr(session, 'started_at', None)

                    major_stages2 = ['case_presentation', 'examination_selection', 'diagnosis_reasoning', 'treatment_selection', 'learning_feedback']

                    # 计算阶段开始：优先 stage_start_times，其次 stage_times 的 to_stage 首次进入；case_presentation 用 run_started_at
                    stage_start_dt2 = {}
                    try:
                        sst2 = stage_start_times or {}
                        if not isinstance(sst2, dict):
                            sst2 = {}
                        inferred_to_stage2 = {}
                        st2 = stage_times or {}
                        if isinstance(st2, dict):
                            for k, v in st2.items():
                                m = re.match(r'^(.+)_to_(.+)$', str(k))
                                if not m:
                                    continue
                                to_stage = m.group(2)
                                dtv = _parse_dt2(v)
                                if dtv is None:
                                    continue
                                if to_stage not in inferred_to_stage2 or dtv < inferred_to_stage2[to_stage]:
                                    inferred_to_stage2[to_stage] = dtv

                        for stg in major_stages2:
                            dtv = _parse_dt2(sst2.get(stg)) or inferred_to_stage2.get(stg)
                            if dtv is None and stg == 'case_presentation':
                                dtv = run_started_at2
                            stage_start_dt2[stg] = dtv
                    except Exception:
                        stage_start_dt2 = {stg: (run_started_at2 if stg == 'case_presentation' else None) for stg in major_stages2}

                    # 计算阶段结束：选“开始之后最近的下一事件（其他阶段开始/会话结束）”
                    stage_end_dt2 = {}
                    all_starts2 = [dt for dt in stage_start_dt2.values() if dt is not None]
                    for stg in major_stages2:
                        sdt = stage_start_dt2.get(stg)
                        if sdt is None:
                            stage_end_dt2[stg] = None
                            continue
                        candidates = [dt for dt in all_starts2 if dt > sdt]
                        if end_time2 is not None and end_time2 > sdt:
                            candidates.append(end_time2)
                        stage_end_dt2[stg] = min(candidates) if candidates else end_time2

                    # 生成 durations
                    stage_durations_ms = {}
                    for stg in major_stages2:
                        sdt = stage_start_dt2.get(stg)
                        edt = stage_end_dt2.get(stg)
                        if not sdt or not edt or edt < sdt:
                            stage_durations_ms[stg] = None
                            continue
                        ms = int((edt - sdt).total_seconds() * 1000)
                        if ms < 0 or ms > 24 * 60 * 60 * 1000:
                            stage_durations_ms[stg] = None
                        else:
                            stage_durations_ms[stg] = ms
                except Exception:
                    stage_durations_ms = None

                # selected_treatments 可能来自 session_data['treatment'] 或 M2M/list
                selected_treatment_ids = []
                try:
                    selected_treats_obj = getattr(session, 'selected_treatments', None)
                    if isinstance(treatment_record, dict) and treatment_record.get('treatment_ids'):
                        selected_treatment_ids = list(treatment_record.get('treatment_ids') or [])
                    elif hasattr(selected_treats_obj, 'values_list'):
                        selected_treatment_ids = list(selected_treats_obj.values_list('id', flat=True))
                    else:
                        selected_treatment_ids = list(selected_treats_obj or [])
                except Exception:
                    selected_treatment_ids = []

                selected_treatment_details = []
                if selected_treatment_ids:
                    try:
                        from cases.models import TreatmentOption
                        rows = list(TreatmentOption.objects.filter(id__in=selected_treatment_ids).values('id', 'treatment_name'))
                        id_to_name = {row['id']: row.get('treatment_name') for row in rows}
                        selected_treatment_details = [
                            {'id': int(tid), 'name': id_to_name.get(int(tid)) or f'治疗#{tid}'}
                            for tid in selected_treatment_ids
                        ]
                    except Exception:
                        selected_treatment_details = [{'id': int(tid), 'name': f'治疗#{tid}'} for tid in selected_treatment_ids]

                review_payload = {
                    'selected_examinations': selected_exam_details,
                    'diagnosis': diagnosis_record,
                    'selected_treatments': selected_treatment_details,
                    'treatment': treatment_record,
                    'stage_times': stage_times,
                    'stage_start_times': stage_start_times,
                    'stage_durations_ms': stage_durations_ms,
                    'session_started_at': review_payload.get('session_started_at'),
                    'session_completed_at': review_payload.get('session_completed_at'),
                    'session_last_activity_at': review_payload.get('session_last_activity_at'),
                    'session_total_ms': review_payload.get('session_total_ms'),
                    **({'debug_time': debug_time} if debug_time_enabled else {}),
                }
            except Exception:
                # 保持 review_payload 默认值，确保接口继续成功返回
                pass
            progress_data = {
                'session_status': getattr(session, 'session_status', None),
                'step_data': getattr(session, 'step_data', None) or {},
                'examination_score': getattr(session, 'examination_score', None),
                'diagnosis_score': getattr(session, 'diagnosis_score', None),
                'treatment_score': getattr(session, 'treatment_score', None),
                'overall_score': getattr(session, 'overall_score', None),
                'review': review_payload,
            }
            return JsonResponse({'success': True, 'data': progress_data})
        except StudentClinicalSession.DoesNotExist:
            return JsonResponse({'success': True, 'data': {'session_status': 'case_presentation'}})
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
    
    # 为每个病例添加统计数据（注意：多表 join 会导致 Count 被放大，必须 distinct）
    from django.db.models import Count, Avg
    cases = cases.annotate(
        examination_count=Count('examination_options', distinct=True),
        diagnosis_count=Count('diagnosis_options', distinct=True),
        treatment_count=Count('treatment_options', distinct=True),
        student_sessions_count=Count('studentclinicalsession', distinct=True),
        completed_sessions_count=Count(
            'studentclinicalsession',
            filter=Q(studentclinicalsession__completed_at__isnull=False),
            distinct=True,
        ),
        avg_score=Avg(
            'studentclinicalsession__overall_score',
            filter=Q(studentclinicalsession__overall_score__gt=0),
        ),
    )
    
    # 分页
    from django.core.paginator import Paginator
    paginator = Paginator(cases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 为分页后的每个病例补齐展示字段（不再做额外查询，避免 N+1）
    for case in page_obj:
        total_sessions = int(getattr(case, 'student_sessions_count', 0) or 0)
        completed_sessions = int(getattr(case, 'completed_sessions_count', 0) or 0)
        case.completion_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0
        case.avg_score = float(getattr(case, 'avg_score', 0) or 0)
    
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
    
    # 调试信息（可根据需要开启）
    # print(f"删除请求 - 用户: {request.user.username}, 方法: {request.method}, 案例: {case_id}")
    
    case = get_object_or_404(ClinicalCase, case_id=case_id)
    
    # 获取相关数据统计
    student_sessions_count = StudentClinicalSession.objects.filter(clinical_case=case).count()
    completed_sessions_count = StudentClinicalSession.objects.filter(
        clinical_case=case, 
        completed_at__isnull=False
    ).count()
    
    if request.method == 'POST':
        # 检查是否勾选了确认删除
        if not request.POST.get('confirm_delete'):
            messages.error(request, '请勾选确认删除选项')
            return render(request, 'teacher/clinical_case_delete.html', {
                'case': case,
                'student_sessions_count': student_sessions_count,
                'completed_sessions_count': completed_sessions_count,
            })
        
        case_title = case.title
        try:
            case.delete()
            messages.success(request, f'临床推理病例 "{case_title}" 已删除')
            return redirect('teacher_clinical_case_list')
        except Exception as e:
            messages.error(request, f'删除失败: {str(e)}')
            return render(request, 'teacher/clinical_case_delete.html', {
                'case': case,
                'student_sessions_count': student_sessions_count,
                'completed_sessions_count': completed_sessions_count,
            })
    
    context = {
        'case': case,
        'student_sessions_count': student_sessions_count,
        'completed_sessions_count': completed_sessions_count,
    }
    return render(request, 'teacher/clinical_case_delete.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_clinical_case_scores(request, case_id):
    """教师端：查看某个病例的学生成绩情况（会话列表）。"""
    clinical_case = get_object_or_404(ClinicalCase, case_id=case_id)

    sessions_qs = (
        StudentClinicalSession.objects.select_related('student', 'clinical_case')
        .filter(clinical_case=clinical_case)
        .order_by('-last_activity')
    )

    # 分页（避免学生很多时卡顿）
    from django.core.paginator import Paginator
    paginator = Paginator(sessions_qs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    items = []
    for session in page_obj:
        case_minutes = _get_session_study_time_minutes(session)
        items.append(
            {
                'session': session,
                'study_time': _format_minutes_as_hm(case_minutes) if isinstance(case_minutes, int) else '-',
            }
        )

    # 汇总：平均分（与列表页一致，统计 overall_score>0）
    from django.db.models import Avg
    avg_score = (
        sessions_qs.filter(overall_score__gt=0)
        .aggregate(Avg('overall_score'))
        .get('overall_score__avg')
        or 0
    )

    context = {
        'clinical_case': clinical_case,
        'page_obj': page_obj,
        'items': items,
        'avg_score': float(avg_score or 0),
        'total_sessions': sessions_qs.count(),
        'completed_sessions': sessions_qs.filter(Q(session_status='completed') | Q(completed_at__isnull=False)).count(),
    }
    return render(request, 'teacher/clinical_case_scores.html', context)


@login_required
def test_delete_view(request):
    """测试删除功能的简单页面"""
    return render(request, 'test_delete.html')


@login_required
def frontend_delete_test(request):
    """前端删除功能测试页面"""
    return render(request, 'frontend_delete_test.html')


@login_required
def simple_delete_test(request):
    """简单删除功能测试"""
    return render(request, 'simple_delete_test.html')


# ==================== 系统管理功能 ====================

@login_required
@user_passes_test(is_teacher, login_url='login')
def system_management(request):
    """系统管理主页面"""
    from django.contrib.auth.models import User, Group
    
    # 统计数据
    total_users = User.objects.count()
    teachers_count = User.objects.filter(groups__name='Teachers').count()
    students_count = User.objects.filter(groups__name='Students').count()
    superusers_count = User.objects.filter(is_superuser=True).count()
    
    # 最近注册的用户
    recent_users = User.objects.order_by('-date_joined')[:10]
    
    # 活跃用户统计
    from datetime import datetime, timedelta
    last_30_days = datetime.now() - timedelta(days=30)
    active_users = User.objects.filter(last_login__gte=last_30_days).count()
    
    context = {
        'total_users': total_users,
        'teachers_count': teachers_count,
        'students_count': students_count,
        'superusers_count': superusers_count,
        'active_users': active_users,
        'recent_users': recent_users,
    }
    
    return render(request, 'teacher/system_management.html', context)


@login_required  
@user_passes_test(is_teacher, login_url='login')
def user_management(request):
    """用户管理页面"""
    from django.contrib.auth.models import User, Group
    from django.db.models import Q
    from django.contrib import messages
    from django.shortcuts import redirect
    
    print(f"[DEBUG] ===== user_management 被调用 =====")
    print(f"[DEBUG] 请求方法: {request.method}")
    print(f"[DEBUG] 请求路径: {request.path}")
    
    # 处理POST请求（权限管理和删除用户）
    if request.method == 'POST':
        # 添加调试输出
        print(f"[DEBUG] POST请求收到: {dict(request.POST)}")
        action = request.POST.get('action')
        print(f"[DEBUG] 操作类型: {action}")
        
        if action == 'change_role':
            user_id = request.POST.get('user_id')
            role = request.POST.get('role')
            is_active = request.POST.get('is_active') == 'on'
            is_superuser = request.POST.get('is_superuser') == 'on'
            
            try:
                user_obj = User.objects.get(id=user_id)
                
                # 更新用户状态
                user_obj.is_active = is_active
                user_obj.is_superuser = is_superuser
                user_obj.save()
                
                # 更新用户组
                user_obj.groups.clear()
                if role == 'teacher':
                    teacher_group, created = Group.objects.get_or_create(name='Teachers')
                    user_obj.groups.add(teacher_group)
                elif role == 'student':
                    student_group, created = Group.objects.get_or_create(name='Students')
                    user_obj.groups.add(student_group)
                
                messages.success(request, f'用户 {user_obj.username} 的权限已更新')
                
            except User.DoesNotExist:
                messages.error(request, '用户不存在')
            except Exception as e:
                messages.error(request, f'更新失败：{str(e)}')
            
            return redirect('user_management')
                
        elif action == 'delete_user':
            user_id = request.POST.get('user_id')
            print(f"[DEBUG] 准备删除用户ID: {user_id}")
            
            try:
                user_obj = User.objects.get(id=user_id)
                print(f"[DEBUG] 找到用户: {user_obj.username}, is_superuser={user_obj.is_superuser}")
                
                # 防止删除超级管理员
                if user_obj.is_superuser:
                    print(f"[DEBUG] 阻止删除超级管理员")
                    messages.error(request, '不能删除超级管理员')
                else:
                    username = user_obj.username
                    user_obj.delete()
                    print(f"[DEBUG] 用户 {username} 已成功删除")
                    messages.success(request, f'用户 {username} 已被删除')
                    
            except User.DoesNotExist:
                messages.error(request, '用户不存在')
                print(f"[DEBUG] 错误: 用户ID {user_id} 不存在")
            except Exception as e:
                messages.error(request, f'删除失败：{str(e)}')
                print(f"[DEBUG] 删除异常: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # 删除操作后重定向,避免重复提交
            return redirect('user_management')
                
        elif action == 'add_user':
            username = request.POST.get('username')
            email = request.POST.get('email', '')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            password = request.POST.get('password')
            role = request.POST.get('role')
            is_active = request.POST.get('is_active') == 'on'
            
            try:
                # 验证用户名是否已存在
                if User.objects.filter(username=username).exists():
                    messages.error(request, f'用户名 {username} 已存在')
                elif not username or not password or not role:
                    messages.error(request, '用户名、密码和角色为必填项')
                else:
                    # 创建新用户
                    user_obj = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        is_active=is_active
                    )
                    
                    # 设置用户组
                    if role == 'teacher':
                        teacher_group, created = Group.objects.get_or_create(name='Teachers')
                        user_obj.groups.add(teacher_group)
                    elif role == 'student':
                        student_group, created = Group.objects.get_or_create(name='Students')
                        user_obj.groups.add(student_group)
                    
                    messages.success(request, f'用户 {username} 创建成功')
                    
            except Exception as e:
                messages.error(request, f'创建用户失败：{str(e)}')
            
            return redirect('user_management')
        
        elif action == 'reset_password':
            user_id = request.POST.get('user_id')
            
            try:
                user_obj = User.objects.get(id=user_id)
                
                # 生成新密码（8位随机密码）
                import random
                import string
                new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                
                # 设置新密码
                user_obj.set_password(new_password)
                user_obj.save()
                
                # 将新密码显示给管理员（通过session临时存储）
                request.session['reset_password_info'] = {
                    'username': user_obj.username,
                    'new_password': new_password
                }
                
                messages.success(request, f'用户 {user_obj.username} 的密码已重置')
                
            except User.DoesNotExist:
                messages.error(request, '用户不存在')
            except Exception as e:
                messages.error(request, f'重置密码失败：{str(e)}')
            
            return redirect('user_management')
    
    # 获取搜索和筛选参数
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # 基础查询
    users = User.objects.all().order_by('-date_joined')
    
    # 搜索
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # 角色筛选
    if role_filter == 'teacher':
        users = users.filter(groups__name='Teachers')
    elif role_filter == 'student':
        users = users.filter(groups__name='Students')
    elif role_filter == 'admin':
        users = users.filter(is_superuser=True)
    
    # 状态筛选
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # 分页
    from django.core.paginator import Paginator
    paginator = Paginator(users, 20)  # 每页20个用户
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    # 获取所有组
    groups = Group.objects.all()
    
    # 获取重置密码信息（如果有）
    reset_password_info = request.session.pop('reset_password_info', None)
    
    context = {
        'users': users,
        'groups': groups,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'reset_password_info': reset_password_info,
    }
    
    return render(request, 'teacher/user_management.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def user_detail(request, user_id):
    """用户详情和编辑"""
    from django.contrib.auth.models import User, Group
    
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # 更新用户信息
        user_obj.first_name = request.POST.get('first_name', '')
        user_obj.last_name = request.POST.get('last_name', '')
        user_obj.email = request.POST.get('email', '')
        user_obj.is_active = request.POST.get('is_active') == 'on'
        
        # 更新用户组
        selected_groups = request.POST.getlist('groups')
        user_obj.groups.clear()
        for group_id in selected_groups:
            try:
                group = Group.objects.get(id=group_id)
                user_obj.groups.add(group)
            except Group.DoesNotExist:
                pass
        
        user_obj.save()
        messages.success(request, f'用户 {user_obj.username} 的信息已更新')
        return redirect('user_detail', user_id=user_id)
    
    # 获取用户的学习统计
    user_sessions = StudentClinicalSession.objects.filter(student=user_obj)
    completed_sessions = user_sessions.filter(completed_at__isnull=False).count()
    total_study_time = 0
    
    for session in user_sessions.filter(completed_at__isnull=False):
        if session.completed_at and session.started_at:
            # 使用last_activity作为实际学习结束时间
            if session.last_activity:
                duration = session.last_activity - session.started_at
            else:
                duration = session.completed_at - session.started_at
            
            duration_minutes = duration.total_seconds() / 60
            if duration_minutes > 0:
                total_study_time += duration_minutes
    
    # 格式化学习时长
    hours = int(total_study_time // 60)
    minutes = int(total_study_time % 60)
    formatted_study_time = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
    
    context = {
        'user_obj': user_obj,
        'groups': Group.objects.all(),
        'user_groups': user_obj.groups.all(),
        'completed_sessions': completed_sessions,
        'formatted_study_time': formatted_study_time,
        'recent_sessions': user_sessions.order_by('-started_at')[:5],
    }
    
    return render(request, 'teacher/user_detail.html', context)


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


@login_required
@user_passes_test(is_student, login_url='login')
def student_learning_notes(request):
    """学生端 - 查看学习笔记"""
    
    # 获取该学生的所有临床会话及其笔记
    sessions_with_notes = StudentClinicalSession.objects.filter(
        student=request.user,
        learning_notes__isnull=False
    ).exclude(learning_notes='').select_related('clinical_case').order_by('-last_activity')
    
    context = {
        'sessions_with_notes': sessions_with_notes,
        'total_notes_count': sessions_with_notes.count(),
    }
    
    return render(request, 'student/learning_notes.html', context)


# ==================== 聊天API端点 ====================

@require_POST
@login_required
def chat_api(request, case_id):
    """
    处理聊天消息并返回患者回复
    基于关键词匹配返回预设的患者回答
    """
    try:
        # 解析请求数据
        data = json.loads(request.body)
        message_content = data.get('message', '').strip()
        
        # 🔍 调试日志：显示接收到的数据
        import sys
        sys.stdout.write(f"\n{'='*60}\n")
        sys.stdout.write(f"🔍 Chat API 被调用\n")
        sys.stdout.write(f"用户: {request.user.username}\n")
        sys.stdout.write(f"病例ID: {case_id}\n")
        sys.stdout.write(f"消息: {message_content}\n")
        sys.stdout.flush()
        
        if not message_content:
            return JsonResponse({
                'success': False,
                'error': '消息内容不能为空'
            })
        
        # 获取临床病例和会话
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id)
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={'session_status': 'case_presentation'}
        )
        
        # 🔍 调试日志：显示会话状态
        sys.stdout.write(f"会话状态: '{session.session_status}' (类型: {type(session.session_status).__name__})\n")
        sys.stdout.write(f"会话ID: {session.id}\n")
        sys.stdout.flush()
        
        # 检查当前阶段是否允许聊天（病史采集和检查选择阶段允许，诊断和治疗阶段禁止）
        allowed_chat_stages = ['case_presentation', 'examination_selection', 'examination_results']
        forbidden_chat_stages = ['diagnosis_reasoning', 'treatment_selection', 'learning_feedback', 'completed']
        
        sys.stdout.write(f"允许聊天的阶段: {allowed_chat_stages}\n")
        sys.stdout.write(f"禁止聊天的阶段: {forbidden_chat_stages}\n")
        sys.stdout.write(f"session.session_status in forbidden_chat_stages: {session.session_status in forbidden_chat_stages}\n")
        sys.stdout.flush()
        
        if session.session_status in forbidden_chat_stages:
            sys.stdout.write(f"❌ 阶段检查失败: '{session.session_status}' 在禁止列表中\n")
            sys.stdout.write(f"{'='*60}\n")
            sys.stdout.flush()
            return JsonResponse({
                'success': False,
                'error': '当前阶段不允许聊天输入'
            })
        
        sys.stdout.write(f"✓ 阶段检查通过: '{session.session_status}' 允许聊天\n")
        sys.stdout.flush()
        
        # 保存学生问题
        student_message = ChatMessage.objects.create(
            session=session,
            message_type='student_question',
            content=message_content,
            stage=session.session_status
        )
        
        # 基于病历库数据进行关键词匹配找到最佳回答
        import sys
        sys.stdout.write(f"\n{'='*50}\n")
        sys.stdout.write(f"📞 调用匹配函数\n")
        sys.stdout.write(f"问题: {message_content}\n")
        sys.stdout.write(f"阶段: {session.session_status}\n")
        sys.stdout.write(f"病例ID: {clinical_case.case_id}\n")
        sys.stdout.flush()
        
        patient_response = find_best_patient_response_from_case(clinical_case, message_content, session.session_status)
        
        sys.stdout.write(f"🎯 匹配结果: {patient_response}\n")
        sys.stdout.flush()
        
        if patient_response:
            # 保存匹配到的患者回答
            response_message = ChatMessage.objects.create(
                session=session,
                message_type='patient_response',
                content=patient_response['text'],
                stage=session.session_status,
                matched_keywords=patient_response.get('keywords', []),
                confidence_score=patient_response.get('confidence', 0.0)
            )
            
            return JsonResponse({
                'success': True,
                'response': {
                    'id': response_message.id,
                    'content': patient_response['text'],
                    'timestamp': response_message.timestamp.isoformat(),
                    'confidence': patient_response.get('confidence', 0.0),
                    'matched_keywords': patient_response.get('keywords', [])
                }
            })
        else:
            # 没有匹配到合适的回答，返回默认回复
            default_response = get_default_patient_response(session.session_status)
            response_message = ChatMessage.objects.create(
                session=session,
                message_type='patient_response',
                content=default_response,
                stage=session.session_status,
                confidence_score=0.1
            )
            
            return JsonResponse({
                'success': True,
                'response': {
                    'id': response_message.id,
                    'content': default_response,
                    'timestamp': response_message.timestamp.isoformat(),
                    'confidence': 0.1,
                    'matched_keywords': []
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        })


def find_best_patient_response_from_case(clinical_case, question, stage):
    """
    基于病历库数据和关键词匹配找到最佳的患者回答
    直接从病例的病史信息中提取相关内容作为回答
    """
    import sys
    sys.stdout.write(f"\n{'='*60}\n")
    sys.stdout.write(f"🔍 查找患者回答\n")
    sys.stdout.write(f"  问题: {question}\n")
    sys.stdout.write(f"  阶段: {stage}\n")
    sys.stdout.write(f"  病例: {clinical_case.case_id}\n")
    sys.stdout.write(f"{'='*60}\n\n")
    sys.stdout.flush()
    
    # 预处理问题文本
    question_normalized = normalize_text(question)
    question_words = question_normalized.split()
    
    # 根据不同阶段匹配不同的病史字段
    # 支持新旧两种阶段命名
    case_fields = {
        'history': {
            'chief_complaint': clinical_case.chief_complaint,
            'present_illness': clinical_case.present_illness,
            'past_history': clinical_case.past_history,
            'family_history': clinical_case.family_history,
        },
        'case_presentation': {  # 新的阶段名
            'chief_complaint': clinical_case.chief_complaint,
            'present_illness': clinical_case.present_illness,
            'past_history': clinical_case.past_history,
            'family_history': clinical_case.family_history,
        },
        'examination': {
            'chief_complaint': clinical_case.chief_complaint,
            'present_illness': clinical_case.present_illness,
        },
        'examination_selection': {  # 新的阶段名
            'chief_complaint': clinical_case.chief_complaint,
            'present_illness': clinical_case.present_illness,
        },
        'examination_results': {  # 新的阶段名
            'chief_complaint': clinical_case.chief_complaint,
            'present_illness': clinical_case.present_illness,
        }
    }
    
    # 默认使用病史阶段的字段
    fields_to_search = case_fields.get(stage, case_fields.get('history', {}))
    
    best_match = None
    highest_confidence = 0.0
    
    # 为不同类型的问题定义关键词和对应的回答模式
    question_patterns = {
        '症状': ['症状', '不舒服', '舒服', '感觉', '疼', '痛', '胀', '痒', '干', '涩', '模糊', '看不清', '哪里', '什么地方', '哪儿', '怎么了'],
        '时间': ['什么时候', '多长时间', '多久', '几天', '几个月', '几年', '开始', '持续'],
        '程度': ['严重', '轻微', '厉害', '程度', '怎么样'],
        '诱因': ['为什么', '原因', '怎么回事', '引起', '诱发'],
        '既往史': ['以前', '之前', '历史', '得过', '有没有', '曾经'],
        '家族史': ['家人', '父母', '亲属', '遗传', '家族', '家里', '家庭', '眼病']
    }
    
    # 分析问题类型并匹配相应的病史信息
    for pattern_type, keywords in question_patterns.items():
        pattern_confidence = calculate_keyword_confidence(question_words, keywords)
        
        sys.stdout.write(f"  模式'{pattern_type}': 置信度={pattern_confidence:.2f}\n")
        sys.stdout.flush()
        
        if pattern_confidence > 0.1:  # 如果匹配到某个模式（降低阈值）
            response_text = generate_response_from_case_data(
                clinical_case, pattern_type, fields_to_search, question
            )
            
            sys.stdout.write(f"    ✓ 匹配成功，响应长度={len(response_text) if response_text else 0}\n")
            sys.stdout.flush()
            
            if response_text and pattern_confidence > highest_confidence:
                highest_confidence = pattern_confidence
                best_match = {
                    'text': response_text,
                    'keywords': keywords,
                    'confidence': pattern_confidence
                }
    
    if best_match:
        sys.stdout.write(f"\n✅ 找到最佳匹配:\n")
        sys.stdout.write(f"  置信度: {best_match['confidence']:.2f}\n")
        sys.stdout.write(f"  响应: {best_match['text'][:100]}...\n")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"\n❌ 未找到匹配\n")
        sys.stdout.flush()
    
    return best_match


def calculate_keyword_confidence(question_words, template_keywords):
    """
    计算关键词匹配的置信度
    """
    if not template_keywords or not question_words:
        return 0.0
    
    matched_keywords = 0
    total_keywords = len(template_keywords)
    
    for keyword in template_keywords:
        keyword_normalized = normalize_text(keyword)
        # 检查完整匹配或部分匹配
        for word in question_words:
            if (keyword_normalized in word or 
                word in keyword_normalized or
                keyword_normalized == word):
                matched_keywords += 1
                break
    
    # 基础匹配度
    base_confidence = matched_keywords / total_keywords
    
    # 考虑匹配词汇的权重（医学术语给予更高权重）
    medical_keywords = ['疼', '痛', '肿', '胀', '模糊', '视力', '眼压', '充血', '分泌物', '干涩', '流泪']
    medical_matches = sum(1 for keyword in template_keywords 
                         if any(med in normalize_text(keyword) for med in medical_keywords))
    
    # 调整置信度
    if medical_matches > 0:
        base_confidence *= (1 + medical_matches * 0.1)  # 医学关键词加权
    
    return min(base_confidence, 1.0)


def normalize_text(text):
    """
    文本标准化：转小写，去除标点符号
    """
    import string
    # 去除中英文标点符号
    punctuation = string.punctuation + '，。！？；：""''（）【】《》'
    for p in punctuation:
        text = text.replace(p, ' ')
    return ' '.join(text.lower().split())


def convert_to_patient_speech(medical_text, pattern_type):
    """
    将医学记录转换为患者的第一人称口语化表达
    """
    if not medical_text or not medical_text.strip():
        return None
    
    text = medical_text.strip()
    
    # 针对不同类型采用不同的转换策略
    if pattern_type == '症状':
        # 主诉：转换为第一人称
        # "双眼视力逐渐下降3年，右眼明显。" -> "我双眼视力逐渐下降3年了，右眼更明显。"
        text = text.replace('。', '')
        text = text.replace('，', '，我')
        if not text.startswith('我'):
            text = '我' + text
        # 添加口语化词汇
        text = text.replace('逐渐', '逐渐')
        text = text.replace('明显', '更明显')
        if not text.endswith('。'):
            text += '。'
        return text
    
    elif pattern_type == '时间':
        # 现病史：保持详细但转为第一人称
        # "患者3年前开始..." -> "我3年前开始..."
        text = text.replace('患者', '我')
        text = text.replace('自觉', '')
        text = text.replace('近半年', '最近半年')
        return text
    
    elif pattern_type == '既往史':
        # 既往史：转为第一人称否定/肯定句
        # "无高血压、糖尿病等..." -> "我没有高血压、糖尿病..."
        text = text.replace('无', '我没有')
        text = text.replace('患者', '我')
        text = text.replace('否认', '没有')
        return text
    
    elif pattern_type == '家族史':
        # 家族史：转为家庭描述
        # "无类似家族病史。" -> "我们家里没有人得过类似的病。"
        if '无' in text or '阴性' in text:
            return '我们家里没有人得过类似的眼病。'
        else:
            text = text.replace('患者', '我')
            text = text.replace('家族史', '家里')
            return text
    
    else:
        # 其他情况：基本转换
        text = text.replace('患者', '我')
        return text


def generate_response_from_case_data(clinical_case, pattern_type, case_fields, question):
    """
    根据问题类型从病例数据中生成相应的患者回答
    """
    responses = {
        '症状': {
            'fields': ['chief_complaint'],  # 主诉直接返回
            'direct_return': True,  # 标记直接返回，不提取句子
            'convert_to_speech': True,  # 转换为口语化
            'templates': [
                '{content}'
            ]
        },
        '时间': {
            'fields': ['present_illness'],
            'direct_return': True,  # 直接返回完整现病史
            'convert_to_speech': True,  # 转换为口语化
            'templates': [
                '{content}'
            ]
        },
        '程度': {
            'fields': ['present_illness'],
            'convert_to_speech': True,
            'templates': [
                '{content}'
            ]
        },
        '诱因': {
            'fields': ['present_illness'],
            'convert_to_speech': True,
            'templates': [
                '{content}'
            ]
        },
        '既往史': {
            'fields': ['past_history'],
            'direct_return': True,  # 直接返回完整既往史
            'convert_to_speech': True,  # 转换为口语化
            'templates': [
                '{content}' if case_fields.get('past_history') else '我以前没有类似的病史。'
            ]
        },
        '家族史': {
            'fields': ['family_history'],
            'direct_return': True,  # 直接返回完整家族史
            'convert_to_speech': True,  # 转换为口语化
            'templates': [
                '{content}' if case_fields.get('family_history') else '我们家族没有类似疾病史。'
            ]
        }
    }
    
    pattern_config = responses.get(pattern_type)
    if not pattern_config:
        return None
    
    # 寻找相关内容
    relevant_content = None
    direct_return = pattern_config.get('direct_return', False)
    convert_to_speech = pattern_config.get('convert_to_speech', False)
    
    for field in pattern_config['fields']:
        field_content = case_fields.get(field, '')
        if field_content and field_content.strip():
            # 如果标记为直接返回，直接使用字段内容
            if direct_return:
                relevant_content = field_content.strip()
            else:
                # 否则提取相关句子
                relevant_content = extract_relevant_sentence(field_content, question)
            
            # 转换为患者口语化表达
            if relevant_content and convert_to_speech:
                relevant_content = convert_to_patient_speech(relevant_content, pattern_type)
            
            if relevant_content:
                break
    
    if not relevant_content:
        # 如果没有找到相关内容，返回默认回答
        if pattern_type == '既往史' and not case_fields.get('past_history'):
            return '我以前没有类似的病史。'
        elif pattern_type == '家族史' and not case_fields.get('family_history'):
            return '我们家族没有类似疾病的病史。'
        else:
            return None
    
    # 随机选择一个回答模板
    import random
    template = random.choice(pattern_config['templates'])
    
    # 格式化回答
    if '{content}' in template:
        return template.format(content=relevant_content)
    else:
        return template


def extract_relevant_sentence(text, question):
    """
    从文本中提取与问题最相关的句子或片段
    """
    if not text or not text.strip():
        return None
    
    # 简单的句子分割（可以进一步优化）
    sentences = []
    for sep in ['。', '！', '？', '\n']:
        text = text.replace(sep, '|SPLIT|')
    
    potential_sentences = text.split('|SPLIT|')
    
    question_words = normalize_text(question).split()
    best_sentence = None
    highest_score = 0
    
    for sentence in potential_sentences:
        sentence = sentence.strip()
        if len(sentence) < 3:  # 忽略太短的句子
            continue
            
        sentence_words = normalize_text(sentence).split()
        score = calculate_keyword_confidence(sentence_words, question_words)
        
        if score > highest_score:
            highest_score = score
            best_sentence = sentence
    
    # 如果没有找到匹配度高的句子，返回第一句非空句子
    if not best_sentence or highest_score < 0.1:
        for sentence in potential_sentences:
            sentence = sentence.strip()
            if len(sentence) > 3:
                best_sentence = sentence
                break
    
    return best_sentence[:100] if best_sentence else None  # 限制长度


def get_default_patient_response(stage):
    """
    获取默认的患者回答（当没有匹配到合适回答时使用）
    """
    default_responses = {
        'history': [
            '对不起，我没太理解您的问题，您能换个方式问吗？',
            '我想想...这个问题我需要仔细回忆一下。',
            '您问的这个问题，我觉得可能与我的症状有关，但我不太确定怎么表达。',
            '医生，您能具体一点吗？我想更准确地回答您的问题。'
        ],
        'examination': [
            '医生，我会配合检查的。',
            '好的，请您给我做检查。',
            '我理解需要做这些检查，请您安排。',
            '医生，您觉得需要做什么检查？'
        ]
    }
    
    import random
    responses = default_responses.get(stage, ['我明白了，请您继续。'])
    return random.choice(responses)


@login_required
@user_passes_test(is_student, login_url='login')
@require_POST
def update_session_stage(request, case_id):
    """
    更新学习会话的当前阶段
    """
    try:
        data = json.loads(request.body)
        new_stage = data.get('stage', '').strip()
        
        # 有效的阶段值（前后端已统一命名）
        valid_stages = [
            'case_presentation',
            'examination_selection',
            'examination_results',
            'diagnosis_reasoning',
            'treatment_selection',
            'learning_feedback',
            'completed'
        ]
        
        # 验证阶段值
        if new_stage not in valid_stages:
            return JsonResponse({
                'success': False,
                'error': f'无效的阶段值: {new_stage}。有效值为: {valid_stages}'
            })
        
        # 前后端已统一命名，直接使用
        actual_stage = new_stage
        
        # 获取临床病例和会话
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id)
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={'session_status': actual_stage}
        )

        # 若用户重新回到病史采集（case_presentation），通常表示开始新一轮学习。
        # 为避免继承上一轮计时导致“总用时/阶段用时爆炸”，这里重置本轮计时相关字段。
        # 触发条件：
        # - 明确完成态（learning_feedback/completed 或 completed_at 不为空）后回到病史采集
        # - 或者：当前阶段已是病史采集，但 session_data 里存在后续阶段的旧计时痕迹（常见于刷新/返回第一阶段）
        # - 或者：前端显式传入 restart/reset_timing=true
        try:
            if not session.session_data:
                session.session_data = {}
            old_status = getattr(session, 'session_status', None)
            is_completed_like = (old_status in ('learning_feedback', 'completed')) or (getattr(session, 'completed_at', None) is not None)

            restart_flag = False
            try:
                restart_flag = bool(data.get('restart') or data.get('reset_timing'))
            except Exception:
                restart_flag = False

            # 检测“已回到第一阶段但计时仍残留”的情况：
            # - session_status 已是 case_presentation（前端/刷新可能把视图带回第一阶段）
            # - 但 stage_start_times/stage_times 中已经记录过后续阶段（说明不是第一次进入）
            has_progress_markers = False
            try:
                sst = session.session_data.get('stage_start_times')
                st = session.session_data.get('stage_times')
                if isinstance(sst, dict):
                    has_progress_markers = any(k and str(k) != 'case_presentation' for k in sst.keys())
                if not has_progress_markers and isinstance(st, dict):
                    has_progress_markers = bool(st)
            except Exception:
                has_progress_markers = False

            is_restart_to_case = (actual_stage == 'case_presentation') and (
                restart_flag or is_completed_like or (old_status == 'case_presentation' and has_progress_markers)
            )

            if is_restart_to_case:
                now_iso = timezone.now().isoformat()

                archives = session.session_data.get('timing_archives')
                if not isinstance(archives, list):
                    archives = []
                archives.append({
                    'archived_at': now_iso,
                    'run_started_at': session.session_data.get('run_started_at'),
                    'stage_start_times': session.session_data.get('stage_start_times'),
                    'stage_times': session.session_data.get('stage_times'),
                    'session_status_before': old_status,
                    'completed_at_before': getattr(session, 'completed_at', None).isoformat() if getattr(session, 'completed_at', None) else None,
                })

                session.session_data['timing_archives'] = archives
                session.session_data['run_started_at'] = now_iso
                session.session_data['stage_start_times'] = {}
                session.session_data['stage_times'] = {}
                # 清理完成标记，让新一轮有正确的 end_time 口径
                if getattr(session, 'completed_at', None) is not None:
                    session.completed_at = None
        except Exception:
            pass

        # 初始化本轮开始时间（用于前端/复盘计时对齐）
        if not session.session_data:
            session.session_data = {}
        changed_meta = False
        now_iso = timezone.now().isoformat()
        if not session.session_data.get('run_started_at'):
            # 旧会话首次补齐 run_started_at：为避免历史 stage_times/stage_start_times 污染本轮，先归档再清空
            try:
                existing_stage_times = session.session_data.get('stage_times')
                existing_stage_start_times = session.session_data.get('stage_start_times')
                if (isinstance(existing_stage_times, dict) and existing_stage_times) or (isinstance(existing_stage_start_times, dict) and existing_stage_start_times):
                    archives = session.session_data.get('timing_archives')
                    if not isinstance(archives, list):
                        archives = []
                    archives.append({
                        'archived_at': now_iso,
                        'run_started_at': session.session_data.get('run_started_at'),
                        'stage_start_times': existing_stage_start_times,
                        'stage_times': existing_stage_times,
                        'session_status_before': getattr(session, 'session_status', None),
                        'completed_at_before': getattr(session, 'completed_at', None).isoformat() if getattr(session, 'completed_at', None) else None,
                        'reason': 'init_run_started_at_reset_timing',
                    })
                    session.session_data['timing_archives'] = archives
                    session.session_data['stage_start_times'] = {}
                    session.session_data['stage_times'] = {}
            except Exception:
                pass
            session.session_data['run_started_at'] = now_iso
            changed_meta = True

        # 记录“每个阶段首次进入时间”（即使没有发生 stage 切换，也要写入，避免前端显示（未记录））
        stage_start_times = session.session_data.get('stage_start_times')
        if not isinstance(stage_start_times, dict):
            stage_start_times = {}
        if not stage_start_times.get(actual_stage):
            stage_start_times[actual_stage] = now_iso
            session.session_data['stage_start_times'] = stage_start_times
            changed_meta = True
        
        # 记录阶段切换时间
        if session.session_status != actual_stage:
            old_stage = session.session_status
            session.session_status = actual_stage
            
            # 更新时间记录
            stage_times = session.session_data.get('stage_times', {})
            stage_times[f'{old_stage}_to_{new_stage}'] = now_iso
            session.session_data['stage_times'] = stage_times
            
            # 如果进入检查阶段，重置检查相关的错误计数
            if actual_stage == 'examination_selection':
                session.session_data.pop('examination_current_attempt_count', None)
                session.session_data.pop('examination_selection_errors', None)
            
            session.save()
            
            return JsonResponse({
                'success': True,
                'message': f'已切换到{new_stage}阶段',
                'data': {
                    'old_stage': old_stage,
                    'new_stage': new_stage,
                    'actual_stage': actual_stage,
                    'timestamp': timezone.now().isoformat()
                }
            })
        else:
            # 阶段未切换，但如果补齐了 run_started_at / stage_start_times，也需要落库
            if changed_meta:
                session.save()
            return JsonResponse({
                'success': True,
                'message': f'已在{new_stage}阶段',
                'data': {
                    'current_stage': new_stage,
                    'actual_stage': actual_stage
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'更新阶段失败: {str(e)}'
        })


@require_POST 
def save_history_summary(request, case_id):
    """
    保存病史汇总信息
    """
    try:
        data = json.loads(request.body)
        
        # 获取临床病例和会话
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id)
        session, created = StudentClinicalSession.objects.get_or_create(
            student=request.user,
            clinical_case=clinical_case,
            defaults={'session_status': 'case_presentation'}
        )
        
        # 保存病史汇总信息
        if not session.session_data:
            session.session_data = {}
        
        history_summary = session.session_data.get('history_summary', {})
        
        # 更新各项病史信息
        if 'chief_complaint' in data:
            history_summary['chief_complaint'] = data['chief_complaint']
        if 'duration' in data:
            history_summary['duration'] = data['duration']
        if 'symptom_nature' in data:
            history_summary['symptom_nature'] = data['symptom_nature']
        if 'severity' in data:
            history_summary['severity'] = data['severity']
        if 'trigger_factors' in data:
            history_summary['trigger_factors'] = data['trigger_factors']
        if 'past_history' in data:
            history_summary['past_history'] = data['past_history']
        if 'family_history' in data:
            history_summary['family_history'] = data['family_history']
            
        session.session_data['history_summary'] = history_summary
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '病史汇总已保存',
            'data': {
                'history_summary': history_summary
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'保存病史汇总失败: {str(e)}'
        })


def get_history_summary(request, case_id):
    """
    获取病史汇总信息
    """
    try:
        # 阶段反向映射：模型值 -> 前端值
        reverse_stage_mapping = {
            'case_presentation': 'history',
            'examination_selection': 'examination',
            'examination_results': 'examination',
            'diagnosis_reasoning': 'diagnosis',
            'treatment_selection': 'treatment',
            'learning_feedback': 'feedback',
            'completed': 'completed'
        }
        
        # 获取临床病例和会话
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id)
        session = get_object_or_404(
            StudentClinicalSession,
            student=request.user,
            clinical_case=clinical_case
        )
        
        history_summary = {}
        if session.session_data:
            history_summary = session.session_data.get('history_summary', {})
        
        # 将数据库中的阶段值映射回前端使用的值
        frontend_stage = reverse_stage_mapping.get(session.session_status, 'history')
        
        return JsonResponse({
            'success': True,
            'data': {
                'history_summary': history_summary,
                'current_stage': frontend_stage
            }
        })
        
    except StudentClinicalSession.DoesNotExist:
        return JsonResponse({
            'success': True,
            'data': {
                'history_summary': {},
                'current_stage': 'history'
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取病史汇总失败: {str(e)}'
        })


@require_http_methods(["GET"])
def get_physical_exam(request, case_id):
    """
    获取体格检查结果
    """
    try:
        # 获取临床病例
        clinical_case = get_object_or_404(ClinicalCase, case_id=case_id)
        
        # 构建体格检查结果
        physical_exam_data = {
            'visual_acuity': clinical_case.visual_acuity or '未记录',
            'intraocular_pressure': clinical_case.intraocular_pressure or '未记录',
            'external_eye': clinical_case.external_eye_exam or '未记录',
            'pupil': clinical_case.pupil_exam or '未记录',
            'conjunctiva': clinical_case.conjunctiva_exam or '未记录',
            'cornea': clinical_case.cornea_exam or '未记录'
        }
        
        return JsonResponse({
            'success': True,
            'data': physical_exam_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取体格检查信息失败: {str(e)}'
        })
