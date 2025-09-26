from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.utils.translation import gettext_lazy as _
from .models import Case, Exercise, Exam, ExamRecord, UserProgress, UserAnswer, ExamResult

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


