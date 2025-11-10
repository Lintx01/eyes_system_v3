from django.urls import path
from . import views

urlpatterns = [
    # 基础页面
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('change-password/', views.change_password_view, name='change_password'),
    
    # Django默认登录URL兼容性路由
    path('accounts/login/', views.login_view, name='account_login'),
    path('accounts/logout/', views.logout_view, name='account_logout'),
    
    # 学生端
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/clinical-cases/', views.clinical_case_list_view, name='clinical_case_list'),
    
    # 教师端
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    
    # 测试页面
    path('test-delete/', views.test_delete_view, name='test_delete'),
    path('frontend-test/', views.frontend_delete_test, name='frontend_test'),
    path('simple-delete-test/', views.simple_delete_test, name='simple_delete_test'),
    
    # 系统管理
    path('system/', views.system_management, name='system_management'),
    path('system/users/', views.user_management, name='user_management'),
    path('system/users/<int:user_id>/', views.user_detail, name='user_detail'),
    
    # 教师端 - 临床推理病例管理
    path('teacher/clinical-cases/', views.teacher_clinical_case_list, name='teacher_clinical_case_list'),
    path('teacher/clinical-cases/create/', views.teacher_clinical_case_create, name='teacher_clinical_case_create'),
    path('teacher/clinical-cases/<str:case_id>/edit/', views.teacher_clinical_case_edit, name='teacher_clinical_case_edit'),
    path('teacher/clinical-cases/<str:case_id>/delete/', views.teacher_clinical_case_delete, name='teacher_clinical_case_delete'),
    path('teacher/clinical-cases/<str:case_id>/preview/', views.teacher_clinical_case_preview, name='teacher_clinical_case_preview'),
    
    # 教师端 - 检查选项管理
    path('teacher/clinical-cases/<str:case_id>/examinations/', views.teacher_examination_options, name='teacher_examination_options'),
    path('teacher/examinations/create/<str:case_id>/', views.teacher_examination_create, name='teacher_examination_create'),
    path('teacher/examinations/<int:exam_id>/edit/', views.teacher_examination_edit, name='teacher_examination_edit'),
    path('teacher/examinations/<int:exam_id>/delete/', views.teacher_examination_delete, name='teacher_examination_delete'),
    path('teacher/clinical-cases/<str:case_id>/batch-set-required/', views.teacher_batch_set_required, name='teacher_batch_set_required'),
    
    # 教师端 - 诊断选项管理
    path('teacher/clinical-cases/<str:case_id>/diagnosis/', views.teacher_diagnosis_options, name='teacher_diagnosis_options'),
    path('teacher/diagnosis/create/<str:case_id>/', views.teacher_diagnosis_create, name='teacher_diagnosis_create'),
    path('teacher/diagnosis/<int:diagnosis_id>/edit/', views.teacher_diagnosis_edit, name='teacher_diagnosis_edit'),
    path('teacher/diagnosis/<int:diagnosis_id>/delete/', views.teacher_diagnosis_delete, name='teacher_diagnosis_delete'),
    
    # 教师端 - 治疗方案管理
    path('teacher/clinical-cases/<str:case_id>/treatments/', views.teacher_treatment_options, name='teacher_treatment_options'),
    path('teacher/treatments/create/<str:case_id>/', views.teacher_treatment_create, name='teacher_treatment_create'),
    path('teacher/treatments/<int:treatment_id>/edit/', views.teacher_treatment_edit, name='teacher_treatment_edit'),
    path('teacher/treatments/<int:treatment_id>/delete/', views.teacher_treatment_delete, name='teacher_treatment_delete'),
    
    # 临床推理系统API
    path('api/clinical/case/<str:case_id>/', views.clinical_case_detail, name='clinical_case_detail'),
    path('api/clinical/case/<str:case_id>/examinations/', views.get_examination_options, name='get_examination_options'),
    path('api/clinical/case/<str:case_id>/examination/<int:exam_id>/', views.get_examination_result, name='get_examination_result'),
    path('api/clinical/confirm-examination-selection/', views.confirm_examination_selection, name='confirm_examination_selection'),
    path('api/clinical/submit-examinations/', views.submit_examination_choices, name='submit_examination_choices'),
    path('api/clinical/submit-diagnosis/', views.submit_diagnosis_choice, name='submit_diagnosis_choice'),
    path('api/clinical/submit-treatments/', views.submit_treatment_choices, name='submit_treatment_choices'),
    path('api/clinical/progress/<str:case_id>/', views.get_clinical_learning_progress, name='get_clinical_learning_progress'),
    path('api/clinical/cases/', views.clinical_cases_list, name='clinical_cases_list'),
    path('api/clinical/user-stats/', views.clinical_user_stats, name='clinical_user_stats'),
    
    # 学习进度管理API
    path('api/clinical/save-progress/', views.save_clinical_progress, name='save_clinical_progress'),
    
    # 临床笔记API
    path('api/clinical/notes/save/', views.save_clinical_notes, name='save_clinical_notes'),
    path('api/clinical/notes/<str:case_id>/', views.get_clinical_notes, name='get_clinical_notes'),
    
    # 学习笔记查看页面
    path('student/learning-notes/', views.student_learning_notes, name='student_learning_notes'),
    path('api/clinical/get-progress/<str:case_id>/', views.get_clinical_progress, name='get_clinical_progress'),
    path('api/clinical/reset-progress/', views.reset_clinical_progress, name='reset_clinical_progress'),

    # 学生端临床推理页面
    path('student/clinical/<str:case_id>/', views.student_clinical_view, name='student_clinical_view'),
    path('clinical-debug/', views.clinical_debug_view, name='clinical_debug'),
]