from django.urls import path
from . import views

urlpatterns = [
    # 基础页面
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Django默认登录URL兼容性路由
    path('accounts/login/', views.login_view, name='account_login'),
    path('accounts/logout/', views.logout_view, name='account_logout'),
    
    # 学生端
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/cases/', views.student_case_list, name='student_case_list'),
    path('student/cases/<int:case_id>/', views.student_case_detail, name='student_case_detail'),
    path('student/clinical-cases/', views.clinical_case_list_view, name='clinical_case_list'),
    path('student/exercises/', views.student_exercise_list, name='student_exercise_list'),
    path('student/exercise/<int:exercise_id>/', views.student_exercise, name='student_exercise'),
    
    # 学生端考试系统
    path('student/exams/', views.student_exam_list, name='student_exam_list'),
    path('student/exams/<int:exam_id>/', views.student_exam_detail, name='student_exam_detail'),
    path('student/exams/<int:exam_id>/start/', views.student_exam_start, name='student_exam_start'),
    path('student/exams/<int:exam_id>/submit/', views.student_exam_submit, name='student_exam_submit'),
    path('student/exams/<int:exam_id>/result/', views.student_exam_result, name='student_exam_result'),
    path('student/results/', views.student_results, name='student_results'),
    
    # 教师端
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/cases/', views.teacher_case_list, name='teacher_case_list'),
    path('teacher/cases/create/', views.teacher_case_create, name='teacher_case_create'),
    path('teacher/cases/create_traditional/', views.teacher_create_traditional_case, name='teacher_create_traditional_case'),
    path('teacher/cases/<int:case_id>/edit/', views.teacher_case_edit, name='teacher_case_edit'),
    path('teacher/cases/<int:case_id>/delete/', views.teacher_case_delete, name='teacher_case_delete'),
    path('teacher/cases/<int:case_id>/exercises/', views.teacher_exercise_list, name='teacher_exercise_list'),
    path('teacher/cases/<int:case_id>/exercises/create/', views.teacher_exercise_create, name='teacher_exercise_create'),
    path('teacher/exercises/<int:exercise_id>/edit/', views.teacher_exercise_edit, name='teacher_exercise_edit'),
    path('teacher/exercises/<int:exercise_id>/delete/', views.teacher_exercise_delete, name='teacher_exercise_delete'),

    # 教师端 - 临床案例专属管理路由（编辑/删除/练习列表）
    path('teacher/clinical/<str:case_id>/edit/', views.teacher_clinical_edit, name='teacher_clinical_edit'),
    path('teacher/clinical/<str:case_id>/delete/', views.teacher_clinical_delete, name='teacher_clinical_delete'),
    path('teacher/clinical/<str:case_id>/exercises/', views.teacher_clinical_exercise_list, name='teacher_clinical_exercise_list'),
    
    # 教师端考试系统
    path('teacher/exams/', views.teacher_exam_list, name='teacher_exam_list'),
    path('teacher/exams/create/', views.teacher_exam_create, name='teacher_exam_create'),
    path('teacher/exams/<int:exam_id>/edit/', views.teacher_exam_edit, name='teacher_exam_edit'),
    path('teacher/exams/<int:exam_id>/delete/', views.teacher_exam_delete, name='teacher_exam_delete'),
    path('teacher/exams/<int:exam_id>/records/', views.teacher_exam_records, name='teacher_exam_records'),
    path('teacher/exams/<int:exam_id>/records/<int:record_id>/', views.teacher_exam_record_detail, name='teacher_exam_record_detail'),
    
    # 统计报表
    path('teacher/reports/', views.teacher_reports, name='teacher_reports'),
    path('teacher/reports/students/', views.teacher_student_reports, name='teacher_student_reports'),
    path('teacher/reports/exams/', views.teacher_exam_reports, name='teacher_exam_reports'),
    path('teacher/reports/export/', views.teacher_report_export, name='teacher_report_export'),
    
    # 教师端 - 学生进度查看
    path('teacher/students/progress/', views.teacher_student_progress_list, name='teacher_student_progress_list'),
    path('teacher/students/<int:student_id>/detail/', views.teacher_student_detail, name='teacher_student_detail'),
    path('teacher/students/progress/export/', views.export_student_progress, name='export_student_progress'),
    
    # 数据导入
    path('teacher/import/cases/', views.import_cases, name='import_cases'),
    
    # 学生端 - 模拟考试功能
    path('student/mock-exam/', views.student_mock_exam_list, name='student_mock_exam_list'),
    path('student/mock-exam/start/', views.start_mock_exam, name='start_mock_exam'),
    path('student/mock-exam/take/', views.take_mock_exam, name='take_mock_exam'),
    path('student/mock-exam/submit/', views.submit_mock_exam, name='submit_mock_exam'),
    path('student/mock-exam/result/<int:result_id>/', views.mock_exam_result, name='mock_exam_result'),
    
    # AJAX接口
    path('api/cases/<int:case_id>/exercises/', views.get_case_exercises, name='get_case_exercises'),
    path('api/exams/<int:exam_id>/timer/', views.get_exam_timer, name='get_exam_timer'),
    
    # 新增AJAX接口
    path('api/user/progress/', views.get_user_progress, name='get_user_progress'),
    path('api/exercise/save-answer/', views.save_exercise_answer, name='save_exercise_answer'),
    path('api/exercise/<int:exercise_id>/statistics/', views.get_exercise_statistics, name='get_exercise_statistics'),
    path('api/exam/<int:exam_id>/status/', views.real_time_exam_status, name='real_time_exam_status'),
    
    # 临床推理系统API
    path('api/clinical/case/<str:case_id>/', views.clinical_case_detail, name='clinical_case_detail'),
    path('api/clinical/case/<str:case_id>/examinations/', views.get_examination_options, name='get_examination_options'),
    path('api/clinical/submit-examinations/', views.submit_examination_choices, name='submit_examination_choices'),
    path('api/clinical/submit-diagnosis/', views.submit_diagnosis_choice, name='submit_diagnosis_choice'),
    path('api/clinical/submit-treatments/', views.submit_treatment_choices, name='submit_treatment_choices'),
    path('api/clinical/progress/<str:case_id>/', views.get_clinical_learning_progress, name='get_clinical_learning_progress'),
    path('api/clinical/cases/', views.clinical_cases_list, name='clinical_cases_list'),
    path('api/clinical/user-stats/', views.clinical_user_stats, name='clinical_user_stats'),
    
    # 新增：学习进度管理API
    path('api/clinical/save-progress/', views.save_clinical_progress, name='save_clinical_progress'),
    path('api/clinical/get-progress/<str:case_id>/', views.get_clinical_progress, name='get_clinical_progress'),
    path('api/clinical/reset-progress/', views.reset_clinical_progress, name='reset_clinical_progress'),

    # 学生端临床推理页面
    path('student/clinical/<str:case_id>/', views.student_clinical_view, name='student_clinical_view'),
    path('clinical-debug/', views.clinical_debug_view, name='clinical_debug'),
]