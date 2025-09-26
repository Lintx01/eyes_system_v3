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
    path('teacher/cases/<int:case_id>/edit/', views.teacher_case_edit, name='teacher_case_edit'),
    path('teacher/cases/<int:case_id>/delete/', views.teacher_case_delete, name='teacher_case_delete'),
    path('teacher/cases/<int:case_id>/exercises/', views.teacher_exercise_list, name='teacher_exercise_list'),
    path('teacher/cases/<int:case_id>/exercises/create/', views.teacher_exercise_create, name='teacher_exercise_create'),
    path('teacher/exercises/<int:exercise_id>/edit/', views.teacher_exercise_edit, name='teacher_exercise_edit'),
    path('teacher/exercises/<int:exercise_id>/delete/', views.teacher_exercise_delete, name='teacher_exercise_delete'),
    
    # 兼容性重定向 - 旧的学生进度URL
    path('teacher/students/progress/old/', views.teacher_student_progress, name='teacher_student_progress'),
    
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
]