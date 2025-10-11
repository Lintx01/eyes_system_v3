from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.utils.translation import gettext_lazy as _
from .models import (
    Case, Exercise, Exam, ExamRecord, UserProgress, UserAnswer, ExamResult,
    ClinicalCase, ExaminationOption, DiagnosisOption, TreatmentOption, 
    StudentClinicalSession, TeachingFeedback
)

# 自定义 AdminSite 以加载自定义 CSS
class CustomAdminSite(AdminSite):
	site_header = "眼科临床训练系统后台"
	site_title = "眼科临床训练系统后台"
	index_title = "管理后台"

	def each_context(self, request):
		context = super().each_context(request)
		context["admin_custom_css"] = "/static/admin_custom.css"
		return context

	def get_urls(self):
		from django.urls import path
		urls = super().get_urls()
		return urls

custom_admin_site = CustomAdminSite(name='custom_admin')


class CaseAdmin(admin.ModelAdmin):
    """病例管理"""
    list_display = ['title', 'difficulty', 'case_type', 'is_active', 'created_at']
    list_filter = ['difficulty', 'case_type', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'symptoms']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'description', 'difficulty', 'case_type', 'is_active')
        }),
        ('临床信息', {
            'fields': ('symptoms', 'diagnosis', 'image')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ExerciseAdmin(admin.ModelAdmin):
    """练习题目管理"""
    list_display = ['question_preview', 'case', 'question_type', 'difficulty', 'is_active', 'created_at']
    list_filter = ['question_type', 'difficulty', 'is_active', 'case']
    search_fields = ['question', 'case__title']
    readonly_fields = ['created_at']
    
    def question_preview(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_preview.short_description = '题干预览'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('case', 'question_type', 'difficulty', 'is_active')
        }),
        ('题目内容', {
            'fields': ('question', 'options', 'correct_answer', 'explanation')
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class ExamAdmin(admin.ModelAdmin):
    """考试管理"""
    list_display = ['title', 'status', 'start_time', 'duration', 'get_questions_count', 'created_by']
    list_filter = ['status', 'start_time', 'created_by']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['exercises', 'participants']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'description', 'status', 'created_by')
        }),
        ('考试设置', {
            'fields': ('start_time', 'duration', 'total_score', 'pass_score')
        }),
        ('题目设置', {
            'fields': ('exercises',)
        }),
        ('权限设置', {
            'fields': ('participants',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ExamRecordAdmin(admin.ModelAdmin):
    """考试记录管理"""
    list_display = ['user', 'exam', 'exam_type', 'score', 'total_questions', 'correct_answers', 
                   'is_completed', 'created_at']
    list_filter = ['exam_type', 'is_completed', 'created_at', 'exam']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'exam__title']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    
    fieldsets = (
        ('考试信息', {
            'fields': ('exam', 'user', 'exam_type', 'is_completed')
        }),
        ('成绩信息', {
            'fields': ('score', 'total_questions', 'correct_answers', 'time_spent')
        }),
        ('关联题目', {
            'fields': ('exercises',)
        }),
        ('时间信息', {
            'fields': ('started_at', 'completed_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )


class UserProgressAdmin(admin.ModelAdmin):
    """用户进度管理"""
    list_display = ['user', 'progress_percentage', 'completed_cases_count', 
                   'completed_exercises_count', 'total_study_time', 'last_study_date']
    list_filter = ['last_study_date', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'last_study_date']
    
    def completed_cases_count(self, obj):
        return obj.completed_cases.count()
    completed_cases_count.short_description = '完成病例数'
    
    def completed_exercises_count(self, obj):
        return obj.completed_exercises.count()
    completed_exercises_count.short_description = '完成练习数'


class UserAnswerAdmin(admin.ModelAdmin):
    """用户答题记录管理"""
    list_display = ['user', 'exercise_preview', 'user_answer', 'is_correct', 'answer_time']
    list_filter = ['is_correct', 'answer_time', 'exercise__question_type']
    search_fields = ['user__username', 'exercise__question']
    readonly_fields = ['answer_time']
    
    def exercise_preview(self, obj):
        return obj.exercise.question[:30] + '...' if len(obj.exercise.question) > 30 else obj.exercise.question
    exercise_preview.short_description = '题目预览'


class ExamResultAdmin(admin.ModelAdmin):
    """模拟考试结果管理"""
    list_display = ['user', 'score', 'total_questions', 'correct_answers', 
                   'accuracy', 'time_spent', 'created_at']
    list_filter = ['created_at', 'total_questions']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'accuracy']
    
    fieldsets = (
        ('考试信息', {
            'fields': ('user', 'score', 'total_questions', 'correct_answers', 'time_spent')
        }),
        ('题目和答案', {
            'fields': ('questions', 'answers'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# 注册到 custom_admin_site
custom_admin_site.register(Case, CaseAdmin)
custom_admin_site.register(Exercise, ExerciseAdmin)
custom_admin_site.register(Exam, ExamAdmin)
custom_admin_site.register(ExamRecord, ExamRecordAdmin)
custom_admin_site.register(UserProgress, UserProgressAdmin)
custom_admin_site.register(UserAnswer, UserAnswerAdmin)
custom_admin_site.register(ExamResult, ExamResultAdmin)


# ================== 临床推理系统管理配置 ==================

class ClinicalCaseAdmin(admin.ModelAdmin):
    """临床案例管理"""
    list_display = ['case_id', 'title', 'patient_age', 'patient_gender', 'difficulty_level', 'is_active', 'created_by', 'created_at']
    list_filter = ['difficulty_level', 'patient_gender', 'is_active', 'created_at', 'created_by']
    search_fields = ['case_id', 'title', 'chief_complaint', 'present_illness']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['created_by']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('case_id', 'title', 'difficulty_level', 'is_active', 'created_by')
        }),
        ('患者信息', {
            'fields': ('patient_age', 'patient_gender')
        }),
        ('临床信息', {
            'fields': ('chief_complaint', 'present_illness', 'past_history', 'family_history')
        }),
        ('教学设置', {
            'fields': ('learning_objectives', 'case_images')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ExaminationOptionAdmin(admin.ModelAdmin):
    """检查选项管理"""
    list_display = ['clinical_case', 'examination_name', 'examination_type', 'diagnostic_value', 'cost_effectiveness', 'is_recommended', 'display_order']
    list_filter = ['examination_type', 'diagnostic_value', 'cost_effectiveness', 'is_recommended']
    search_fields = ['examination_name', 'examination_description', 'clinical_case__title']
    list_editable = ['display_order', 'is_recommended']
    raw_id_fields = ['clinical_case']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('clinical_case', 'examination_type', 'examination_name', 'examination_description')
        }),
        ('检查结果', {
            'fields': ('normal_result', 'abnormal_result', 'actual_result')
        }),
        ('教学评估', {
            'fields': ('diagnostic_value', 'cost_effectiveness', 'is_recommended')
        }),
        ('显示设置', {
            'fields': ('result_images', 'display_order')
        }),
    )


class DiagnosisOptionAdmin(admin.ModelAdmin):
    """诊断选项管理"""
    list_display = ['clinical_case', 'diagnosis_name', 'is_correct_diagnosis', 'is_differential', 'probability_score', 'display_order']
    list_filter = ['is_correct_diagnosis', 'is_differential']
    search_fields = ['diagnosis_name', 'diagnosis_code', 'clinical_case__title']
    list_editable = ['display_order', 'probability_score']
    raw_id_fields = ['clinical_case']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('clinical_case', 'diagnosis_name', 'diagnosis_code')
        }),
        ('诊断属性', {
            'fields': ('is_correct_diagnosis', 'is_differential', 'probability_score')
        }),
        ('诊断依据', {
            'fields': ('supporting_evidence', 'contradicting_evidence')
        }),
        ('临床特征', {
            'fields': ('typical_symptoms', 'typical_signs')
        }),
        ('教学反馈', {
            'fields': ('correct_feedback', 'incorrect_feedback')
        }),
        ('显示设置', {
            'fields': ('display_order',)
        }),
    )


class TreatmentOptionAdmin(admin.ModelAdmin):
    """治疗选项管理"""
    list_display = ['clinical_case', 'treatment_name', 'treatment_type', 'is_optimal', 'is_acceptable', 'efficacy_score', 'safety_score', 'display_order']
    list_filter = ['treatment_type', 'is_optimal', 'is_acceptable', 'efficacy_score', 'safety_score']
    search_fields = ['treatment_name', 'treatment_description', 'clinical_case__title']
    list_editable = ['display_order']
    raw_id_fields = ['clinical_case', 'related_diagnosis']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('clinical_case', 'related_diagnosis', 'treatment_type', 'treatment_name', 'treatment_description')
        }),
        ('治疗评估', {
            'fields': ('is_optimal', 'is_acceptable', 'is_contraindicated')
        }),
        ('治疗特性', {
            'fields': ('efficacy_score', 'safety_score', 'cost_score')
        }),
        ('预期结果', {
            'fields': ('expected_outcome', 'potential_complications')
        }),
        ('教学反馈', {
            'fields': ('selection_feedback',)
        }),
        ('显示设置', {
            'fields': ('display_order',)
        }),
    )


class StudentClinicalSessionAdmin(admin.ModelAdmin):
    """学生临床会话管理"""
    list_display = ['student', 'clinical_case', 'session_status', 'overall_score', 'started_at', 'completed_at']
    list_filter = ['session_status', 'started_at', 'completed_at']
    search_fields = ['student__username', 'clinical_case__title', 'clinical_case__case_id']
    readonly_fields = ['started_at', 'last_activity', 'overall_score']
    raw_id_fields = ['student', 'clinical_case', 'selected_diagnosis']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('student', 'clinical_case', 'session_status')
        }),
        ('学习轨迹', {
            'fields': ('selected_examinations', 'selected_diagnosis', 'selected_treatments')
        }),
        ('学习评估', {
            'fields': ('examination_score', 'diagnosis_score', 'treatment_score', 'overall_score')
        }),
        ('时间跟踪', {
            'fields': ('time_spent', 'started_at', 'completed_at', 'last_activity')
        }),
        ('学习成果', {
            'fields': ('learning_notes', 'reflection'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.session_status == 'completed':
            return readonly_fields + ('session_status',)
        return readonly_fields


class TeachingFeedbackAdmin(admin.ModelAdmin):
    """教学反馈管理"""
    list_display = ['student_session', 'feedback_stage', 'feedback_type', 'is_automated', 'created_at']
    list_filter = ['feedback_stage', 'feedback_type', 'is_automated', 'created_at']
    search_fields = ['student_session__student__username', 'feedback_content']
    readonly_fields = ['created_at']
    raw_id_fields = ['student_session']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('student_session', 'feedback_stage', 'feedback_type', 'is_automated')
        }),
        ('反馈内容', {
            'fields': ('feedback_content', 'improvement_suggestions')
        }),
        ('相关资源', {
            'fields': ('reference_materials',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# 将临床推理模型注册到管理后台
custom_admin_site.register(ClinicalCase, ClinicalCaseAdmin)
custom_admin_site.register(ExaminationOption, ExaminationOptionAdmin)
custom_admin_site.register(DiagnosisOption, DiagnosisOptionAdmin)
custom_admin_site.register(TreatmentOption, TreatmentOptionAdmin)
custom_admin_site.register(StudentClinicalSession, StudentClinicalSessionAdmin)
custom_admin_site.register(TeachingFeedback, TeachingFeedbackAdmin)


