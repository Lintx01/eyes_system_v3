from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Case, Exercise, Exam, ExamRecord, UserProgress, UserAnswer, ExamResult
import json
import csv
from datetime import datetime, timedelta
import io
import xlsxwriter
import random


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
    
    # 获取或创建用户进度
    progress, created = UserProgress.objects.get_or_create(user=user)
    
    # 统计信息
    total_cases = Case.objects.filter(is_active=True).count()
    completed_cases = progress.completed_cases.filter(is_active=True).count()
    total_exercises = Exercise.objects.filter(is_active=True).count()
    completed_exercises = progress.completed_exercises.filter(is_active=True).count()
    
    # 最近考试记录
    recent_exams = ExamRecord.objects.filter(
        user=user, is_completed=True
    ).order_by('-completed_at')[:5]
    
    context = {
        'progress': progress,
        'total_cases': total_cases,
        'completed_cases': completed_cases,
        'total_exercises': total_exercises,
        'completed_exercises': completed_exercises,
        'recent_exams': recent_exams,
    }
    
    return render(request, 'student/dashboard.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def student_case_list(request):
    """学生病例列表"""
    cases = Case.objects.filter(is_active=True).order_by('-created_at')
    
    # 获取用户进度
    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    completed_cases = set(progress.completed_cases.values_list('id', flat=True))
    
    # 分页
    paginator = Paginator(cases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'completed_cases': completed_cases,
    }
    
    return render(request, 'student/case_list.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def student_case_detail(request, case_id):
    """学生病例详情"""
    case = get_object_or_404(Case, id=case_id, is_active=True)
    exercises = case.exercises.filter(is_active=True)
    
    # 获取用户进度
    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    
    context = {
        'case': case,
        'exercises': exercises,
        'progress': progress,
    }
    
    return render(request, 'student/case_detail.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def student_exercise(request, exercise_id):
    """学生练习页面"""
    exercise = get_object_or_404(Exercise, id=exercise_id, is_active=True)
    
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        
        # 如果是选择题，将数字索引转换为字母
        if exercise.question_type in ['single', 'multiple'] and user_answer.isdigit():
            # 将数字索引转换为对应的字母 (0->A, 1->B, 2->C, 3->D)
            user_answer_letter = chr(int(user_answer) + ord('A'))
        else:
            user_answer_letter = user_answer
        
        # 创建答题记录
        answer_record = UserAnswer.objects.create(
            user=request.user,
            exercise=exercise,
            user_answer=user_answer_letter  # 存储转换后的字母答案
        )
        answer_record.check_answer()
        answer_record.save()
        
        # 更新用户进度
        progress, _ = UserProgress.objects.get_or_create(user=request.user)
        progress.completed_exercises.add(exercise)
        progress.completed_cases.add(exercise.case)
        progress.update_progress()
        
        # 返回结果
        context = {
            'exercise': exercise,
            'user_answer': user_answer,  # 数字索引，用于前端显示
            'user_answer_letter': user_answer_letter,  # 字母答案，用于比较
            'correct_answer': exercise.correct_answer,
            'is_correct': answer_record.is_correct,
            'explanation': exercise.explanation,
        }
        
        return render(request, 'student/exercise_result.html', context)
    
    # 获取选项列表
    options = exercise.get_options_list()
    
    context = {
        'exercise': exercise,
        'options': options,
    }
    
    return render(request, 'student/exercise.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def student_exercise_list(request):
    """学生练习列表"""
    # 获取所有激活的练习题
    exercises = Exercise.objects.filter(is_active=True).select_related('case').order_by('-created_at')
    
    # 获取用户已完成的练习
    user_answers = UserAnswer.objects.filter(user=request.user).values_list('exercise_id', flat=True)
    completed_exercises = set(user_answers)
    
    # 获取用户进度
    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    
    # 分页
    paginator = Paginator(exercises, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'completed_exercises': completed_exercises,
        'total_exercises': exercises.count(),
        'completed_count': len(completed_exercises),
        'progress': progress,
    }
    
    return render(request, 'student/exercise_list.html', context)


# 教师端视图
@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_dashboard(request):
    """教师仪表板"""
    # 统计数据
    total_cases = Case.objects.count()
    active_cases = Case.objects.filter(is_active=True).count()
    total_exercises = Exercise.objects.count()
    total_students = User.objects.filter(groups__name='Students').count()
    
    # 最近活动
    recent_exams = ExamRecord.objects.filter(
        is_completed=True
    ).order_by('-completed_at')[:10]
    
    # 学生进度统计
    avg_progress = UserProgress.objects.aggregate(
        avg_progress=Avg('progress_percentage')
    )['avg_progress'] or 0
    
    context = {
        'total_cases': total_cases,
        'active_cases': active_cases,
        'total_exercises': total_exercises,
        'total_students': total_students,
        'recent_exams': recent_exams,
        'avg_progress': round(avg_progress, 2),
    }
    
    return render(request, 'teacher/dashboard.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_case_list(request):
    """教师病例管理"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    cases = Case.objects.all()
    
    if search:
        cases = cases.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if status == 'active':
        cases = cases.filter(is_active=True)
    elif status == 'inactive':
        cases = cases.filter(is_active=False)
    
    cases = cases.order_by('-created_at')
    
    # 分页
    paginator = Paginator(cases, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
    }
    
    return render(request, 'teacher/case_list.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_case_create(request):
    """教师创建病例"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        symptoms = request.POST.get('symptoms')
        diagnosis = request.POST.get('diagnosis')
        difficulty = request.POST.get('difficulty', 'medium')
        case_type = request.POST.get('case_type', 'clinical')
        image = request.FILES.get('image')
        is_active = request.POST.get('is_active') == 'on'
        
        # 验证必填字段
        if not title or not description or not symptoms:
            messages.error(request, '请填写所有必填字段（病例名称、病例描述、症状表现）')
            return render(request, 'teacher/case_form.html', {
                'title': '创建病例',
                'action': '创建',
                'form_data': request.POST,
            })
        
        case = Case.objects.create(
            title=title,
            description=description,
            symptoms=symptoms,
            diagnosis=diagnosis,
            difficulty=difficulty,
            case_type=case_type,
            image=image,
            is_active=is_active
        )
        
        messages.success(request, f'病例 "{case.title}" 创建成功！')
        return redirect('teacher_case_list')
    
    return render(request, 'teacher/case_form.html', {
        'title': '创建病例',
        'action': '创建',
    })


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_case_edit(request, case_id):
    """教师编辑病例"""
    case = get_object_or_404(Case, id=case_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        symptoms = request.POST.get('symptoms')
        diagnosis = request.POST.get('diagnosis')
        difficulty = request.POST.get('difficulty', case.difficulty)
        case_type = request.POST.get('case_type', case.case_type)
        is_active = request.POST.get('is_active') == 'on'
        
        # 验证必填字段
        if not title or not description or not symptoms:
            messages.error(request, '请填写所有必填字段（病例名称、病例描述、症状表现）')
            return render(request, 'teacher/case_form.html', {
                'case': case,
                'title': '编辑病例',
                'action': '更新',
                'form_data': request.POST,
            })
        
        case.title = title
        case.description = description
        case.symptoms = symptoms
        case.diagnosis = diagnosis
        case.difficulty = difficulty
        case.case_type = case_type
        case.is_active = is_active
        
        if request.FILES.get('image'):
            case.image = request.FILES.get('image')
        
        case.save()
        
        messages.success(request, f'病例 "{case.title}" 更新成功！')
        return redirect('teacher_case_list')
    
    context = {
        'case': case,
        'title': '编辑病例',
        'action': '更新',
    }
    
    return render(request, 'teacher/case_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_case_delete(request, case_id):
    """教师删除病例"""
    if request.method == 'POST':
        case = get_object_or_404(Case, id=case_id)
        case_title = case.title
        case.delete()
        
        messages.success(request, f'病例 "{case_title}" 删除成功！')
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exercise_list(request, case_id):
    """教师练习题目管理"""
    case = get_object_or_404(Case, id=case_id)
    exercises = case.exercises.all().order_by('-created_at')
    
    context = {
        'case': case,
        'exercises': exercises,
    }
    
    return render(request, 'teacher/exercise_list.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exercise_create(request, case_id):
    """教师创建练习题目"""
    case = get_object_or_404(Case, id=case_id)
    
    if request.method == 'POST':
        question = request.POST.get('question')
        question_type = request.POST.get('question_type')
        correct_answer = request.POST.get('correct_answer')
        explanation = request.POST.get('explanation', '')
        difficulty = int(request.POST.get('difficulty', 1))
        is_active = request.POST.get('is_active') == 'on'
        
        # 处理选项
        options = []
        if question_type in ['single', 'multiple']:
            for i in range(1, 7):  # 最多6个选项
                option = request.POST.get(f'option_{i}')
                if option and option.strip():
                    options.append(option.strip())
        elif question_type == 'judge':
            options = ['正确', '错误']
        
        # 验证必填字段
        if not question or not question_type or not correct_answer:
            messages.error(request, '请填写所有必填字段')
            return render(request, 'teacher/exercise_form.html', {
                'case': case,
                'title': '创建练习题目',
                'action': '创建',
                'form_data': request.POST,
            })
        
        # 验证选项
        if question_type in ['single', 'multiple'] and len(options) < 2:
            messages.error(request, '选择题至少需要2个选项')
            return render(request, 'teacher/exercise_form.html', {
                'case': case,
                'title': '创建练习题目',
                'action': '创建',
                'form_data': request.POST,
            })
        
        exercise = Exercise.objects.create(
            case=case,
            question=question,
            question_type=question_type,
            correct_answer=correct_answer,
            explanation=explanation,
            difficulty=difficulty,
            is_active=is_active
        )
        exercise.set_options_list(options)
        exercise.save()
        
        messages.success(request, f'练习题目创建成功！')
        return redirect('teacher_exercise_list', case_id=case.id)
    
    context = {
        'case': case,
        'title': '创建练习题目',
        'action': '创建',
    }
    
    return render(request, 'teacher/exercise_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exercise_edit(request, exercise_id):
    """教师编辑练习题目"""
    exercise = get_object_or_404(Exercise, id=exercise_id)
    case = exercise.case
    
    if request.method == 'POST':
        question = request.POST.get('question')
        question_type = request.POST.get('question_type')
        correct_answer = request.POST.get('correct_answer')
        explanation = request.POST.get('explanation', '')
        difficulty = int(request.POST.get('difficulty', exercise.difficulty))
        is_active = request.POST.get('is_active') == 'on'
        
        # 处理选项
        options = []
        if question_type in ['single', 'multiple']:
            for i in range(1, 7):  # 最多6个选项
                option = request.POST.get(f'option_{i}')
                if option and option.strip():
                    options.append(option.strip())
        elif question_type == 'judge':
            options = ['正确', '错误']
        
        # 验证必填字段
        if not question or not question_type or not correct_answer:
            messages.error(request, '请填写所有必填字段')
            return render(request, 'teacher/exercise_form.html', {
                'case': case,
                'exercise': exercise,
                'title': '编辑练习题目',
                'action': '更新',
                'form_data': request.POST,
            })
        
        # 验证选项
        if question_type in ['single', 'multiple'] and len(options) < 2:
            messages.error(request, '选择题至少需要2个选项')
            return render(request, 'teacher/exercise_form.html', {
                'case': case,
                'exercise': exercise,
                'title': '编辑练习题目',
                'action': '更新',
                'form_data': request.POST,
            })
        
        exercise.question = question
        exercise.question_type = question_type
        exercise.correct_answer = correct_answer
        exercise.explanation = explanation
        exercise.difficulty = difficulty
        exercise.is_active = is_active
        exercise.set_options_list(options)
        exercise.save()
        
        messages.success(request, f'练习题目更新成功！')
        return redirect('teacher_exercise_list', case_id=case.id)
    
    context = {
        'case': case,
        'exercise': exercise,
        'title': '编辑练习题目',
        'action': '更新',
    }
    
    return render(request, 'teacher/exercise_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exercise_delete(request, exercise_id):
    """教师删除练习题目"""
    if request.method == 'POST':
        exercise = get_object_or_404(Exercise, id=exercise_id)
        case_id = exercise.case.id
        question_preview = exercise.question[:50]
        exercise.delete()
        
        messages.success(request, f'练习题目 "{question_preview}..." 删除成功！')
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_student_progress(request):
    """教师查看学生进度"""
    students = User.objects.filter(groups__name='Students')
    progress_data = []
    
    for student in students:
        progress, _ = UserProgress.objects.get_or_create(user=student)
        recent_exam = ExamRecord.objects.filter(
            user=student, is_completed=True
        ).order_by('-completed_at').first()
        
        progress_data.append({
            'student': student,
            'progress': progress,
            'recent_exam': recent_exam,
        })
    
    context = {
        'progress_data': progress_data,
    }
    
    return render(request, 'teacher/student_progress.html', context)


# 数据导入功能
@login_required
@user_passes_test(is_teacher, login_url='login')
def import_cases(request):
    """批量导入病例"""
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, '请选择要导入的CSV文件')
            return redirect('teacher_case_list')
        
        csv_file = request.FILES['csv_file']
        
        try:
            # 读取CSV文件
            decoded_file = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(decoded_file.splitlines())
            
            imported_count = 0
            for row in reader:
                Case.objects.create(
                    name=row['病例名称'],
                    description=row['病例描述'],
                    symptoms=row['症状表现'],
                    exams=row['检查结果'],
                    is_active=row.get('是否启用', 'True').lower() == 'true'
                )
                imported_count += 1
            
            messages.success(request, f'成功导入 {imported_count} 个病例')
            
        except Exception as e:
            messages.error(request, f'导入失败：{str(e)}')
    
    return redirect('teacher_case_list')


# AJAX视图
@login_required
def get_case_exercises(request, case_id):
    """获取病例的练习题目（AJAX）"""
    case = get_object_or_404(Case, id=case_id, is_active=True)
    exercises = case.exercises.filter(is_active=True).values(
        'id', 'question', 'question_type', 'difficulty'
    )
    
    return JsonResponse({
        'exercises': list(exercises),
        'case_name': case.name,
    })


# === 考试系统视图 ===

# 学生端考试系统
@login_required
@user_passes_test(is_student, login_url='login')
def student_exam_list(request):
    """学生考试列表"""
    now = timezone.now()
    
    # 可参加的考试
    available_exams = Exam.objects.filter(
        status='published'
    ).exclude(
        records__user=request.user  # 排除已参加的考试
    ).order_by('start_time')
    
    # 已参加的考试
    completed_exams = ExamRecord.objects.filter(
        user=request.user, 
        is_completed=True
    ).select_related('exam').order_by('-completed_at')[:10]
    
    context = {
        'available_exams': available_exams,
        'completed_exams': completed_exams,
        'now': now,
    }
    
    return render(request, 'student/exam_list.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def student_exam_detail(request, exam_id):
    """学生考试详情页"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    # 检查是否已参加过此考试
    existing_record = ExamRecord.objects.filter(
        exam=exam, user=request.user
    ).first()
    
    if existing_record:
        return redirect('student_exam_result', exam_id=exam.id)
    
    now = timezone.now()
    
    # 计算考试状态
    exam.auto_update_status()
    
    context = {
        'exam': exam,
        'now': now,
        'can_start': exam.can_start,
        'is_finished': exam.is_finished,
    }
    
    return render(request, 'student/exam_detail.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def student_exam_start(request, exam_id):
    """学生开始考试"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    # 检查考试状态
    if not exam.can_start:
        messages.error(request, '考试尚未开始或已结束')
        return redirect('student_exam_detail', exam_id=exam.id)
    
    # 检查是否已参加
    existing_record = ExamRecord.objects.filter(
        exam=exam, user=request.user
    ).first()
    
    if existing_record:
        return redirect('student_exam_result', exam_id=exam.id)
    
    # 创建考试记录
    exam_record = ExamRecord.objects.create(
        exam=exam,
        user=request.user,
        exam_type='exam',
        total_questions=exam.exercises.count(),
        start_time=timezone.now()
    )
    
    # 添加考试题目
    exam_record.exercises.set(exam.exercises.all())
    
    # 获取题目列表
    exercises = exam.exercises.filter(is_active=True).order_by('id')
    
    context = {
        'exam': exam,
        'exam_record': exam_record,
        'exercises': exercises,
        'end_time': exam.end_time,
    }
    
    return render(request, 'student/exam_taking.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
@transaction.atomic
def student_exam_submit(request, exam_id):
    """学生提交考试答案"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method != 'POST':
        return redirect('student_exam_detail', exam_id=exam.id)
    
    # 获取考试记录
    exam_record = get_object_or_404(
        ExamRecord, 
        exam=exam, 
        user=request.user, 
        is_completed=False
    )
    
    # 自动评分算法
    correct_answers = 0
    total_questions = exam_record.total_questions
    
    # 处理每道题的答案
    for exercise in exam_record.exercises.all():
        user_answer = request.POST.get(f'exercise_{exercise.id}', '').strip()
        
        if user_answer:
            # 创建答题记录
            answer_record = UserAnswer.objects.create(
                user=request.user,
                exercise=exercise,
                exam_record=exam_record,
                user_answer=user_answer
            )
            
            # 检查答案正确性
            is_correct = answer_record.check_answer()
            answer_record.save()
            
            if is_correct:
                correct_answers += 1
    
    # 更新考试记录
    exam_record.correct_answers = correct_answers
    exam_record.submit_time = timezone.now()
    exam_record.is_completed = True
    
    # 计算得分和用时
    exam_record.calculate_score()
    exam_record.calculate_time_spent()
    exam_record.save()
    
    messages.success(request, '考试提交成功！')
    return redirect('student_exam_result', exam_id=exam.id)


@login_required
@user_passes_test(is_student, login_url='login')
def student_exam_result(request, exam_id):
    """学生查看考试结果"""
    exam = get_object_or_404(Exam, id=exam_id)
    exam_record = get_object_or_404(
        ExamRecord, 
        exam=exam, 
        user=request.user
    )
    
    # 获取答题详情
    answers = UserAnswer.objects.filter(
        exam_record=exam_record
    ).select_related('exercise')
    
    context = {
        'exam': exam,
        'exam_record': exam_record,
        'answers': answers,
    }
    
    return render(request, 'student/exam_result.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def student_results(request):
    """学生查看所有考试结果"""
    exam_records = ExamRecord.objects.filter(
        user=request.user, 
        is_completed=True
    ).select_related('exam').order_by('-completed_at')
    
    # 分页
    paginator = Paginator(exam_records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'student/results.html', context)


# 教师端考试管理
@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exam_list(request):
    """教师考试管理列表"""
    exams = Exam.objects.all().order_by('-created_at')
    
    # 分页
    paginator = Paginator(exams, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'teacher/exam_list.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exam_create(request):
    """教师创建考试"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        start_time_str = request.POST.get('start_time')
        duration = int(request.POST.get('duration', 60))
        total_score = float(request.POST.get('total_score', 100))
        pass_score = float(request.POST.get('pass_score', 60))
        exercise_ids = request.POST.getlist('exercises')
        
        try:
            # 解析开始时间
            start_time = timezone.datetime.strptime(
                start_time_str, '%Y-%m-%dT%H:%M'
            )
            start_time = timezone.make_aware(start_time)
            
            # 创建考试
            exam = Exam.objects.create(
                title=title,
                description=description,
                start_time=start_time,
                duration=duration,
                total_score=total_score,
                pass_score=pass_score,
                status='published',
                created_by=request.user
            )
            
            # 添加题目
            if exercise_ids:
                exercises = Exercise.objects.filter(
                    id__in=exercise_ids, 
                    is_active=True
                )
                exam.exercises.set(exercises)
            
            messages.success(request, f'考试 "{exam.title}" 创建成功！')
            return redirect('teacher_exam_list')
            
        except ValueError as e:
            messages.error(request, '时间格式错误，请重新选择')
    
    # 获取可选的练习题目
    exercises = Exercise.objects.filter(is_active=True).select_related('case')
    
    context = {
        'exercises': exercises,
    }
    
    return render(request, 'teacher/exam_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exam_edit(request, exam_id):
    """教师编辑考试"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        exam.title = request.POST.get('title')
        exam.description = request.POST.get('description', '')
        exam.duration = int(request.POST.get('duration', 60))
        exam.total_score = float(request.POST.get('total_score', 100))
        exam.pass_score = float(request.POST.get('pass_score', 60))
        exam.status = request.POST.get('status', 'draft')
        
        start_time_str = request.POST.get('start_time')
        if start_time_str:
            try:
                start_time = timezone.datetime.strptime(
                    start_time_str, '%Y-%m-%dT%H:%M'
                )
                exam.start_time = timezone.make_aware(start_time)
            except ValueError:
                messages.error(request, '时间格式错误')
                return render(request, 'teacher/exam_form.html', {
                    'exam': exam,
                    'exercises': Exercise.objects.filter(is_active=True).select_related('case')
                })
        
        exercise_ids = request.POST.getlist('exercises')
        if exercise_ids:
            exercises = Exercise.objects.filter(
                id__in=exercise_ids, 
                is_active=True
            )
            exam.exercises.set(exercises)
        
        exam.save()
        
        messages.success(request, f'考试 "{exam.title}" 更新成功！')
        return redirect('teacher_exam_list')
    
    # 获取可选的练习题目
    exercises = Exercise.objects.filter(is_active=True).select_related('case')
    selected_exercise_ids = list(exam.exercises.values_list('id', flat=True))
    
    context = {
        'exam': exam,
        'exercises': exercises,
        'selected_exercise_ids': selected_exercise_ids,
    }
    
    return render(request, 'teacher/exam_form.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exam_delete(request, exam_id):
    """教师删除考试"""
    if request.method == 'POST':
        exam = get_object_or_404(Exam, id=exam_id)
        exam_title = exam.title
        exam.delete()
        
        messages.success(request, f'考试 "{exam_title}" 删除成功！')
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exam_records(request, exam_id):
    """教师查看考试成绩"""
    exam = get_object_or_404(Exam, id=exam_id)
    records = exam.records.select_related('user').order_by('-score', 'submit_time')
    
    # 统计数据
    total_participants = records.filter(is_completed=True).count()
    passed_count = records.filter(is_passed=True).count()
    pass_rate = round((passed_count / total_participants * 100), 2) if total_participants > 0 else 0
    avg_score = records.filter(is_completed=True).aggregate(
        avg=Avg('score')
    )['avg'] or 0
    
    context = {
        'exam': exam,
        'records': records,
        'total_participants': total_participants,
        'passed_count': passed_count,
        'pass_rate': pass_rate,
        'avg_score': round(avg_score, 2),
    }
    
    return render(request, 'teacher/exam_records.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exam_record_detail(request, exam_id, record_id):
    """教师查看单个学生的考试详情"""
    exam = get_object_or_404(Exam, id=exam_id)
    record = get_object_or_404(ExamRecord, id=record_id, exam=exam)
    
    # 获取答题详情
    answers = UserAnswer.objects.filter(
        exam_record=record
    ).select_related('exercise').order_by('exercise__id')
    
    context = {
        'exam': exam,
        'record': record,
        'answers': answers,
    }
    
    return render(request, 'teacher/exam_record_detail.html', context)


# === 统计报表系统 ===

@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_reports(request):
    """教师统计报表总览"""
    # 基本统计数据
    total_students = User.objects.filter(groups__name='Students').count()
    total_cases = Case.objects.filter(is_active=True).count()
    total_exercises = Exercise.objects.filter(is_active=True).count()
    total_exams = Exam.objects.count()
    
    # 学生活跃度统计
    active_students = UserProgress.objects.filter(
        last_study_date__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # 考试统计
    recent_exams = ExamRecord.objects.filter(
        completed_at__gte=timezone.now() - timedelta(days=30),
        is_completed=True
    )
    avg_recent_score = recent_exams.aggregate(avg=Avg('score'))['avg'] or 0
    
    context = {
        'total_students': total_students,
        'total_cases': total_cases,
        'total_exercises': total_exercises,
        'total_exams': total_exams,
        'active_students': active_students,
        'avg_recent_score': round(avg_recent_score, 2),
        'recent_exam_count': recent_exams.count(),
    }
    
    return render(request, 'teacher/reports.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_student_reports(request):
    """学生学习统计报表"""
    # 筛选参数
    student_id = request.GET.get('student_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # 获取学生列表
    students = User.objects.filter(groups__name='Students').order_by('username')
    
    # 构建查询
    student_filter = Q()
    if student_id:
        student_filter = Q(id=student_id)
    
    # 获取学生数据
    report_data = []
    filtered_students = students.filter(student_filter) if student_id else students
    
    for student in filtered_students:
        progress, _ = UserProgress.objects.get_or_create(user=student)
        
        # 考试记录筛选
        exam_query = ExamRecord.objects.filter(user=student, is_completed=True)
        if date_from:
            exam_query = exam_query.filter(completed_at__gte=date_from)
        if date_to:
            exam_query = exam_query.filter(completed_at__lte=date_to)
        
        exam_records = exam_query.order_by('completed_at')
        
        # 统计数据
        exam_stats = progress.get_exam_stats()
        avg_score = exam_records.aggregate(avg=Avg('score'))['avg'] or 0
        
        report_data.append({
            'student': student,
            'progress': progress,
            'completed_cases': progress.completed_cases.filter(is_active=True).count(),
            'completed_exercises': progress.completed_exercises.filter(is_active=True).count(),
            'total_exams': exam_stats['total_exams'],
            'passed_exams': exam_stats['passed_exams'],
            'pass_rate': exam_stats['pass_rate'],
            'avg_score': round(avg_score, 2),
            'recent_exams': exam_records[:5],  # 最近5次考试
        })
    
    # 分页
    paginator = Paginator(report_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'students': students,
        'selected_student_id': int(student_id) if student_id else None,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'teacher/student_reports.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_exam_reports(request):
    """考试统计报表"""
    exams = Exam.objects.annotate(
        participant_count=Count('records', filter=Q(records__is_completed=True)),
        avg_score=Avg('records__score', filter=Q(records__is_completed=True)),
        pass_count=Count('records', filter=Q(records__is_passed=True))
    ).order_by('-start_time')
    
    # 分页
    paginator = Paginator(exams, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'teacher/exam_reports.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_report_export(request):
    """导出学生报表为Excel"""
    # 创建Excel文件
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('学生学习报表')
    
    # 设置格式
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D7E4BC',
        'border': 1
    })
    
    # 写入表头
    headers = [
        '学生姓名', '用户名', '学习进度(%)', '完成病例数', 
        '完成练习数', '参加考试数', '通过考试数', '通过率(%)', 
        '平均分', '最后学习时间'
    ]
    
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # 写入数据
    students = User.objects.filter(groups__name='Students').order_by('username')
    row = 1
    
    for student in students:
        progress, _ = UserProgress.objects.get_or_create(user=student)
        exam_stats = progress.get_exam_stats()
        
        data = [
            student.get_full_name() or student.username,
            student.username,
            float(progress.progress_percentage),
            progress.completed_cases.filter(is_active=True).count(),
            progress.completed_exercises.filter(is_active=True).count(),
            exam_stats['total_exams'],
            exam_stats['passed_exams'],
            exam_stats['pass_rate'],
            exam_stats['avg_score'],
            progress.last_study_date.strftime('%Y-%m-%d %H:%M') if progress.last_study_date else ''
        ]
        
        for col, value in enumerate(data):
            worksheet.write(row, col, value)
        row += 1
    
    # 调整列宽
    worksheet.set_column('A:J', 15)
    
    workbook.close()
    output.seek(0)
    
    # 返回Excel文件
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=student_report_{timezone.now().strftime("%Y%m%d")}.xlsx'
    
    return response


@login_required
def get_exam_timer(request, exam_id):
    """获取考试剩余时间（AJAX）"""
    exam = get_object_or_404(Exam, id=exam_id)
    now = timezone.now()
    
    if now < exam.start_time:
        time_left = int((exam.start_time - now).total_seconds())
        status = 'not_started'
    elif now > exam.end_time:
        time_left = 0
        status = 'finished'
    else:
        time_left = int((exam.end_time - now).total_seconds())
        status = 'in_progress'
    
    return JsonResponse({
        'time_left': time_left,
        'status': status,
        'formatted_time': str(timedelta(seconds=time_left))
    })


# ==================== 新增功能：教师端学生进度查看 ====================

@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_student_progress_list(request):
    """教师查看学生进度列表"""
    students = User.objects.filter(groups__name='Students')
    
    progress_data = []
    for student in students:
        progress, _ = UserProgress.objects.get_or_create(user=student)
        
        # 统计练习数据
        total_answers = UserAnswer.objects.filter(user=student).count()
        correct_answers = UserAnswer.objects.filter(user=student, is_correct=True).count()
        accuracy = round((correct_answers / total_answers * 100), 2) if total_answers > 0 else 0
        
        # 最近一次练习时间
        last_answer = UserAnswer.objects.filter(user=student).order_by('-answer_time').first()
        last_practice_time = last_answer.answer_time if last_answer else None
        
        # 模拟考试数据
        exam_results = ExamResult.objects.filter(user=student)
        avg_exam_score = exam_results.aggregate(avg=Avg('score'))['avg'] or 0
        
        progress_data.append({
            'student': student,
            'progress': progress,
            'completed_exercises': total_answers,
            'accuracy': accuracy,
            'last_practice_time': last_practice_time,
            'exam_count': exam_results.count(),
            'avg_exam_score': round(avg_exam_score, 2),
        })
    
    # 排序：按最近练习时间倒序
    # 使用timezone.make_aware创建带时区的最小日期时间作为默认值
    min_datetime = timezone.make_aware(datetime.min)
    progress_data.sort(key=lambda x: x['last_practice_time'] or min_datetime, reverse=True)
    
    # 为模板准备学生数据，添加统计字段到学生对象
    students_with_stats = []
    for data in progress_data:
        student = data['student']
        student.total_study_time = data['progress'].total_study_time or 0
        student.case_study_count = data['progress'].completed_cases.count()
        student.exercise_count = data['completed_exercises']
        student.exam_count = data['exam_count']
        student.mock_exam_count = data['exam_count']  # 模拟考试计数
        student.avg_score = data['avg_exam_score']
        students_with_stats.append(student)
    
    # 计算整体统计数据
    total_students = len(progress_data)
    
    # 根据学习时长和考试成绩分类学生活跃度
    active_count = sum(1 for data in progress_data if data['completed_exercises'] >= 10 and data['avg_exam_score'] >= 80)
    inactive_count = sum(1 for data in progress_data if data['completed_exercises'] < 3 and data['avg_exam_score'] < 60)
    moderate_count = total_students - active_count - inactive_count
    
    # 计算平均学习时间
    total_study_hours = sum(data['progress'].total_study_time or 0 for data in progress_data)
    avg_study_time = round(total_study_hours / max(total_students, 1), 1)
    
    stats = {
        'total_students': total_students,
        'active_students': active_count,
        'moderate_students': moderate_count,
        'inactive_students': inactive_count,
        'avg_study_time': avg_study_time,
        'total_exercises': sum(data['completed_exercises'] for data in progress_data),
        'total_exams': sum(data['exam_count'] for data in progress_data),
    }
    
    context = {
        'students': students_with_stats,
        'progress_data': progress_data,
        'total_students': total_students,
        'stats': stats,
    }
    
    return render(request, 'teacher/student_progress_list.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def teacher_student_detail(request, student_id):
    """教师查看学生详细进度"""
    student = get_object_or_404(User, id=student_id, groups__name='Students')
    progress, _ = UserProgress.objects.get_or_create(user=student)
    
    # 练习记录
    user_answers = UserAnswer.objects.filter(user=student).select_related('exercise__case').order_by('-answer_time')
    
    # 模拟考试记录
    exam_results = ExamResult.objects.filter(user=student).order_by('-created_at')
    
    # 统计数据
    total_exercises = user_answers.count()
    correct_exercises = user_answers.filter(is_correct=True).count()
    accuracy = round((correct_exercises / total_exercises * 100), 2) if total_exercises > 0 else 0
    
    # 按病例分组的练习统计
    case_stats = {}
    for answer in user_answers:
        case = answer.exercise.case
        if case not in case_stats:
            case_stats[case] = {'total': 0, 'correct': 0}
        case_stats[case]['total'] += 1
        if answer.is_correct:
            case_stats[case]['correct'] += 1
    
    # 计算各病例正确率
    for case, stats in case_stats.items():
        stats['accuracy'] = round((stats['correct'] / stats['total'] * 100), 2)
    
    context = {
        'student': student,
        'progress': progress,
        'user_answers': user_answers[:20],  # 显示最近20条
        'exam_results': exam_results,
        'total_exercises': total_exercises,
        'correct_exercises': correct_exercises,
        'accuracy': accuracy,
        'case_stats': case_stats,
    }
    
    return render(request, 'teacher/student_detail.html', context)


@login_required
@user_passes_test(is_teacher, login_url='login')
def export_student_progress(request):
    """导出学生进度Excel"""
    students = User.objects.filter(groups__name='Students')
    
    # 创建Excel文件
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('学生进度统计')
    
    # 设置格式
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D7E4BD',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    # 写入表头
    headers = ['姓名', '用户名', '完成练习数', '正确答案数', '正确率(%)', 
              '模拟考试次数', '平均考试得分', '最近练习时间']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # 写入数据
    for row, student in enumerate(students, 1):
        progress, _ = UserProgress.objects.get_or_create(user=student)
        
        total_answers = UserAnswer.objects.filter(user=student).count()
        correct_answers = UserAnswer.objects.filter(user=student, is_correct=True).count()
        accuracy = round((correct_answers / total_answers * 100), 2) if total_answers > 0 else 0
        
        exam_results = ExamResult.objects.filter(user=student)
        avg_score = exam_results.aggregate(avg=Avg('score'))['avg'] or 0
        
        last_answer = UserAnswer.objects.filter(user=student).order_by('-answer_time').first()
        last_time = last_answer.answer_time.strftime('%Y-%m-%d %H:%M') if last_answer else '无记录'
        
        data = [
            student.get_full_name() or student.username,
            student.username,
            total_answers,
            correct_answers,
            accuracy,
            exam_results.count(),
            round(avg_score, 2),
            last_time
        ]
        
        for col, value in enumerate(data):
            worksheet.write(row, col, value, cell_format)
    
    # 调整列宽
    worksheet.set_column('A:A', 12)
    worksheet.set_column('B:B', 12)
    worksheet.set_column('C:G', 10)
    worksheet.set_column('H:H', 16)
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=学生进度统计_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response


# ==================== 新增功能：学生端模拟考试 ====================

@login_required
@user_passes_test(is_student, login_url='login')
def student_mock_exam_list(request):
    """学生模拟考试列表"""
    # 获取用户的模拟考试历史
    exam_results = ExamResult.objects.filter(user=request.user).order_by('-created_at')
    
    # 获取题库统计信息
    total_exercises = Exercise.objects.filter(is_active=True).count()
    
    context = {
        'exam_results': exam_results,
        'total_exercises': total_exercises,
    }
    
    return render(request, 'student/mock_exam_list.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def start_mock_exam(request):
    """开始模拟考试"""
    if request.method == 'POST':
        question_count = int(request.POST.get('question_count', 20))
        time_limit = int(request.POST.get('time_limit', 30))  # 分钟
        
        # 随机选择题目
        all_exercises = Exercise.objects.filter(is_active=True)
        if all_exercises.count() < question_count:
            messages.error(request, f'题库中只有{all_exercises.count()}道题，少于所需的{question_count}道题')
            return redirect('student_mock_exam_list')
        
        selected_exercises = random.sample(list(all_exercises), question_count)
        
        # 将题目ID存储在session中
        request.session['mock_exam_questions'] = [ex.id for ex in selected_exercises]
        request.session['mock_exam_start_time'] = timezone.now().timestamp()
        request.session['mock_exam_time_limit'] = time_limit
        request.session['mock_exam_answers'] = {}
        
        return redirect('take_mock_exam')
    
    context = {
        'available_exercises': Exercise.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'student/start_mock_exam.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def take_mock_exam(request):
    """进行模拟考试"""
    if 'mock_exam_questions' not in request.session:
        messages.error(request, '没有进行中的模拟考试')
        return redirect('student_mock_exam_list')
    
    if request.method == 'POST':
        # 保存单题答案
        question_id = request.POST.get('question_id')
        answer = request.POST.get('answer')
        
        if question_id and answer:
            if 'mock_exam_answers' not in request.session:
                request.session['mock_exam_answers'] = {}
            request.session['mock_exam_answers'][question_id] = answer
            request.session.modified = True
            
            return JsonResponse({'status': 'success'})
    
    question_ids = request.session['mock_exam_questions']
    exercises = Exercise.objects.filter(id__in=question_ids).prefetch_related('case')
    
    start_time = datetime.fromtimestamp(request.session['mock_exam_start_time'], tz=datetime.timezone.utc)
    time_limit = request.session['mock_exam_time_limit']
    end_time = start_time + timedelta(minutes=time_limit)
    
    # 检查是否超时
    now = timezone.now()
    if now >= end_time:
        return redirect('submit_mock_exam')
    
    time_left = int((end_time - now).total_seconds())
    saved_answers = request.session.get('mock_exam_answers', {})
    
    context = {
        'exercises': exercises,
        'time_left': time_left,
        'saved_answers': saved_answers,
        'total_questions': len(exercises),
    }
    
    return render(request, 'student/take_mock_exam.html', context)


@login_required
@user_passes_test(is_student, login_url='login')
def submit_mock_exam(request):
    """提交模拟考试"""
    if 'mock_exam_questions' not in request.session:
        messages.error(request, '没有进行中的模拟考试')
        return redirect('student_mock_exam_list')
    
    if request.method == 'POST':
        # 批量提交答案
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = key.replace('question_', '')
                if 'mock_exam_answers' not in request.session:
                    request.session['mock_exam_answers'] = {}
                request.session['mock_exam_answers'][question_id] = value
        request.session.modified = True
    
    # 计算成绩
    question_ids = request.session['mock_exam_questions']
    exercises = Exercise.objects.filter(id__in=question_ids)
    answers = request.session.get('mock_exam_answers', {})
    
    start_time = datetime.fromtimestamp(request.session['mock_exam_start_time'], tz=datetime.timezone.utc)
    time_spent = int((timezone.now() - start_time).total_seconds() / 60)  # 转换为分钟
    
    total_questions = len(question_ids)
    correct_count = 0
    answer_details = []
    
    for exercise in exercises:
        user_answer = answers.get(str(exercise.id), '')
        
        # 转换答案格式
        if exercise.question_type in ['single', 'multiple'] and user_answer.isdigit():
            user_answer_letter = chr(int(user_answer) + ord('A'))
        else:
            user_answer_letter = user_answer
        
        is_correct = user_answer_letter.upper() == exercise.correct_answer.upper()
        if is_correct:
            correct_count += 1
        
        answer_details.append({
            'exercise_id': exercise.id,
            'user_answer': user_answer_letter,
            'correct_answer': exercise.correct_answer,
            'is_correct': is_correct
        })
    
    # 计算分数
    score = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    # 保存考试结果
    exam_result = ExamResult.objects.create(
        user=request.user,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_count,
        time_spent=time_spent,
        answers=json.dumps(answer_details, ensure_ascii=False)
    )
    exam_result.questions.set(exercises)
    
    # 清除session数据
    for key in ['mock_exam_questions', 'mock_exam_start_time', 'mock_exam_time_limit', 'mock_exam_answers']:
        request.session.pop(key, None)
    
    return redirect('mock_exam_result', result_id=exam_result.id)


@login_required
@user_passes_test(is_student, login_url='login')
def mock_exam_result(request, result_id):
    """查看模拟考试结果"""
    exam_result = get_object_or_404(ExamResult, id=result_id, user=request.user)
    
    # 解析答题详情
    answer_details = []
    if exam_result.answers:
        try:
            details = json.loads(exam_result.answers)
            for detail in details:
                exercise = Exercise.objects.get(id=detail['exercise_id'])
                answer_details.append({
                    'exercise': exercise,
                    'user_answer': detail['user_answer'],
                    'correct_answer': detail['correct_answer'],
                    'is_correct': detail['is_correct']
                })
        except (json.JSONDecodeError, Exercise.DoesNotExist):
            pass
    
    context = {
        'exam_result': exam_result,
        'answer_details': answer_details,
    }
    
    return render(request, 'student/mock_exam_result.html', context)
