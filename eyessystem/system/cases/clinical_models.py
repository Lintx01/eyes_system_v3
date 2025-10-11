"""
临床推理教学模型
重新设计数据结构，支持完整的临床思维训练流程
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class ClinicalCase(models.Model):
    """临床推理病例模型 - 重新设计的核心模型"""
    
    CASE_STAGES = [
        ('history', '病史采集'),
        ('examination', '体格检查'),
        ('investigation', '辅助检查'),
        ('diagnosis', '鉴别诊断'),
        ('treatment', '治疗决策'),
        ('summary', '总结反馈'),
    ]
    
    # 基础信息
    title = models.CharField('病例标题', max_length=200)
    patient_info = models.JSONField('患者基本信息', default=dict, help_text='年龄、性别、职业等')
    chief_complaint = models.TextField('主诉', help_text='患者主要症状描述')
    
    # 病史信息（分阶段展示）
    present_illness = models.TextField('现病史', help_text='详细病史描述')
    past_history = models.TextField('既往史', blank=True)
    family_history = models.TextField('家族史', blank=True)
    personal_history = models.TextField('个人史', blank=True)
    
    # 临床推理配置
    teaching_objectives = models.TextField('教学目标', help_text='本病例的学习目标')
    key_points = models.JSONField('关键知识点', default=list, help_text='需要掌握的知识点')
    difficulty = models.CharField('难度等级', max_length=10, 
                                 choices=[('beginner', '初学者'), ('intermediate', '中级'), ('advanced', '高级')],
                                 default='intermediate')
    
    # 标准答案和评分
    standard_diagnosis = models.TextField('标准诊断', help_text='权威诊断结果')
    treatment_plan = models.TextField('标准治疗方案')
    prognosis = models.TextField('预后评估', blank=True)
    
    # 教学反馈配置
    common_mistakes = models.JSONField('常见错误', default=list, help_text='学生常犯的错误及纠正')
    references = models.JSONField('参考资料', default=list, help_text='相关指南、教材章节')
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    is_active = models.BooleanField('是否启用', default=True)
    
    class Meta:
        verbose_name = '临床推理病例'
        verbose_name_plural = '临床推理病例'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_difficulty_display()}"


class ExaminationOption(models.Model):
    """检查选项模型 - 支持体格检查和辅助检查"""
    
    EXAM_TYPES = [
        ('physical', '体格检查'),
        ('laboratory', '实验室检查'),
        ('imaging', '影像学检查'),
        ('special', '特殊检查'),
    ]
    
    case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='exam_options')
    exam_type = models.CharField('检查类型', max_length=20, choices=EXAM_TYPES)
    name = models.CharField('检查名称', max_length=100)
    description = models.TextField('检查描述', help_text='检查的具体内容和方法')
    
    # 检查结果
    result = models.TextField('检查结果', help_text='阳性或阴性结果描述')
    normal_range = models.CharField('正常范围', max_length=200, blank=True)
    clinical_significance = models.TextField('临床意义', help_text='该检查对诊断的意义')
    
    # 教学配置
    is_essential = models.BooleanField('是否必要检查', default=False, help_text='诊断该病例是否必需此检查')
    cost = models.IntegerField('检查费用', default=0, help_text='用于成本效益教学')
    risk_level = models.CharField('风险等级', max_length=10, 
                                 choices=[('low', '低风险'), ('medium', '中风险'), ('high', '高风险')],
                                 default='low')
    
    # 智能反馈
    feedback_positive = models.TextField('阳性反馈', help_text='选择此检查的正面反馈')
    feedback_negative = models.TextField('阴性反馈', help_text='不选择此检查的提醒')
    
    order = models.IntegerField('显示顺序', default=0)
    
    class Meta:
        verbose_name = '检查选项'
        verbose_name_plural = '检查选项'
        ordering = ['exam_type', 'order']
    
    def __str__(self):
        return f"{self.get_exam_type_display()} - {self.name}"


class DiagnosisOption(models.Model):
    """诊断选项模型 - 支持鉴别诊断教学"""
    
    case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='diagnosis_options')
    diagnosis_name = models.CharField('诊断名称', max_length=200)
    icd_code = models.CharField('ICD编码', max_length=20, blank=True)
    
    # 诊断支持度
    is_correct = models.BooleanField('是否正确诊断', default=False)
    probability = models.IntegerField('可能性百分比', default=0, 
                                    validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # 诊断依据
    supporting_evidence = models.TextField('支持证据', help_text='支持该诊断的临床表现和检查')
    contradicting_evidence = models.TextField('反对证据', blank=True, help_text='不支持该诊断的证据')
    
    # 教学反馈
    educational_feedback = models.TextField('教学反馈', help_text='选择该诊断的教学指导')
    differential_points = models.TextField('鉴别要点', help_text='与其他疾病的鉴别要点')
    
    order = models.IntegerField('显示顺序', default=0)
    
    class Meta:
        verbose_name = '诊断选项'
        verbose_name_plural = '诊断选项'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.diagnosis_name} ({self.probability}%)"


class TreatmentOption(models.Model):
    """治疗选项模型 - 支持治疗决策教学"""
    
    TREATMENT_TYPES = [
        ('medication', '药物治疗'),
        ('surgery', '手术治疗'),
        ('observation', '观察随访'),
        ('referral', '转诊治疗'),
        ('education', '健康教育'),
    ]
    
    case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='treatment_options')
    treatment_type = models.CharField('治疗类型', max_length=20, choices=TREATMENT_TYPES)
    name = models.CharField('治疗名称', max_length=200)
    description = models.TextField('治疗描述', help_text='具体的治疗方法和步骤')
    
    # 治疗评估
    is_appropriate = models.BooleanField('是否合适', default=True)
    effectiveness = models.IntegerField('有效性评分', default=0,
                                      validators=[MinValueValidator(0), MaxValueValidator(100)])
    side_effects = models.TextField('副作用', blank=True)
    contraindications = models.TextField('禁忌症', blank=True)
    
    # 成本效益
    cost_level = models.CharField('费用水平', max_length=10,
                                 choices=[('low', '低'), ('medium', '中'), ('high', '高')],
                                 default='medium')
    duration = models.CharField('治疗周期', max_length=100, blank=True)
    
    # 教学反馈
    rationale = models.TextField('治疗理由', help_text='选择该治疗的医学依据')
    teaching_feedback = models.TextField('教学反馈', help_text='选择该治疗方案的指导意见')
    
    order = models.IntegerField('显示顺序', default=0)
    
    class Meta:
        verbose_name = '治疗选项'
        verbose_name_plural = '治疗选项'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.get_treatment_type_display()} - {self.name}"


class StudentClinicalSession(models.Model):
    """学生临床推理会话模型 - 记录完整的学习过程"""
    
    SESSION_STATUS = [
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('abandoned', '已放弃'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clinical_sessions')
    case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='student_sessions')
    
    # 会话状态
    status = models.CharField('会话状态', max_length=20, choices=SESSION_STATUS, default='in_progress')
    current_stage = models.CharField('当前阶段', max_length=20, choices=ClinicalCase.CASE_STAGES, default='history')
    
    # 学习路径记录
    selected_examinations = models.ManyToManyField(ExaminationOption, blank=True, verbose_name='已选检查')
    selected_diagnosis = models.ForeignKey(DiagnosisOption, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='选择的诊断')
    selected_treatments = models.ManyToManyField(TreatmentOption, blank=True, verbose_name='选择的治疗')
    
    # 评分和反馈
    total_score = models.DecimalField('总分', max_digits=5, decimal_places=2, default=0.00)
    examination_score = models.DecimalField('检查得分', max_digits=5, decimal_places=2, default=0.00)
    diagnosis_score = models.DecimalField('诊断得分', max_digits=5, decimal_places=2, default=0.00)
    treatment_score = models.DecimalField('治疗得分', max_digits=5, decimal_places=2, default=0.00)
    
    # 学习记录
    learning_path = models.JSONField('学习路径', default=list, help_text='记录学生的完整操作序列')
    feedback_received = models.JSONField('已接收反馈', default=list, help_text='系统给出的所有反馈')
    time_spent = models.IntegerField('用时分钟', default=0)
    
    # 时间记录
    started_at = models.DateTimeField('开始时间', auto_now_add=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    
    class Meta:
        verbose_name = '学生临床会话'
        verbose_name_plural = '学生临床会话'
        ordering = ['-started_at']
    
    def calculate_total_score(self):
        """计算总分"""
        weights = {
            'examination': 0.3,  # 检查选择 30%
            'diagnosis': 0.5,    # 诊断准确性 50%
            'treatment': 0.2,    # 治疗方案 20%
        }
        
        self.total_score = (
            self.examination_score * weights['examination'] +
            self.diagnosis_score * weights['diagnosis'] +
            self.treatment_score * weights['treatment']
        )
        return self.total_score
    
    def add_learning_step(self, stage, action, content):
        """添加学习步骤记录"""
        step = {
            'timestamp': timezone.now().isoformat(),
            'stage': stage,
            'action': action,
            'content': content
        }
        self.learning_path.append(step)
        self.save()
    
    def add_feedback(self, feedback_type, message, score=None):
        """添加系统反馈"""
        feedback = {
            'timestamp': timezone.now().isoformat(),
            'type': feedback_type,
            'message': message,
            'score': score
        }
        self.feedback_received.append(feedback)
        self.save()
    
    def __str__(self):
        return f"{self.student.username} - {self.case.title} ({self.get_status_display()})"


class TeachingFeedback(models.Model):
    """智能教学反馈模型"""
    
    FEEDBACK_TYPES = [
        ('encouragement', '鼓励性反馈'),
        ('guidance', '引导性反馈'),
        ('correction', '纠错性反馈'),
        ('knowledge', '知识点提醒'),
        ('summary', '总结性反馈'),
    ]
    
    case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='teaching_feedbacks')
    trigger_condition = models.CharField('触发条件', max_length=200, help_text='什么情况下显示此反馈')
    feedback_type = models.CharField('反馈类型', max_length=20, choices=FEEDBACK_TYPES)
    
    title = models.CharField('反馈标题', max_length=100)
    content = models.TextField('反馈内容', help_text='具体的教学指导内容')
    
    # 智能匹配
    target_stage = models.CharField('目标阶段', max_length=20, choices=ClinicalCase.CASE_STAGES)
    trigger_score_range = models.CharField('触发分数区间', max_length=20, blank=True, help_text='如"0-60"表示低分时触发')
    
    # 教学资源
    reference_materials = models.JSONField('参考资料', default=list, help_text='相关的学习资源链接')
    related_cases = models.ManyToManyField('self', blank=True, verbose_name='相关病例')
    
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '教学反馈'
        verbose_name_plural = '教学反馈'
        ordering = ['target_stage', 'feedback_type']
    
    def __str__(self):
        return f"{self.get_target_stage_display()} - {self.title}"