from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import SET_NULL
import json


class Case(models.Model):
    """眼科病例模型"""
    title = models.CharField('病例名称', max_length=200, help_text='病例的标题或名称')    # charfield 对应 string的短文本
    description = models.TextField('病例描述', help_text='详细的病例描述和背景信息')    # textfield 对应 string的长文本
    symptoms = models.TextField('症状表现', help_text='患者的主要症状和表现')
    diagnosis = models.TextField('诊断结果', help_text='各项检查的详细结果', default='待补充')
    image = models.ImageField('病例图像', upload_to='case_images/', blank=True, null=True, 
                             help_text='相关的检查图片或眼底照片')    # imagefield 对应 图片类型
    difficulty = models.CharField('难度等级', max_length=10, 
                                 choices=[('easy', '简单'), ('medium', '中等'), ('hard', '困难')],
                                 default='medium', help_text='病例难度等级')
    case_type = models.CharField('病例类型', max_length=20,
                                choices=[('clinical', '临床病例'), ('surgery', '手术病例'), ('emergency', '急诊病例')],
                                default='clinical', help_text='病例类型分类')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)    # datetimefield 对应 日期时间类型
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    is_active = models.BooleanField('是否启用', default=True, help_text='是否在教学中使用此病例') # boolean 对应 bool类型
    
    class Meta:
        verbose_name = '眼科病例'
        verbose_name_plural = '眼科病例'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Exercise(models.Model):
    """练习题目模型"""
    QUESTION_TYPES = [
        ('single', '单选题'),
        ('multiple', '多选题'),
        ('judge', '判断题'),
    ]
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='exercises',
                            verbose_name='关联病例', help_text='此题目关联的病例')  # foreignkey 对应 关联另一个模型
    question = models.TextField('题干', help_text='题目的问题内容')
    question_type = models.CharField('题目类型', max_length=20, choices=QUESTION_TYPES, 
                                    default='single')
    options = models.TextField('选项', help_text='题目选项，JSON格式存储，如：["A选项", "B选项", "C选项", "D选项"]')
    correct_answer = models.CharField('正确答案', max_length=50, 
                             help_text='正确答案，单选填A/B/C/D，多选填AB/AC等，判断题填T/F')
    explanation = models.TextField('答案解析', blank=True, help_text='题目答案的详细解析')
    difficulty = models.IntegerField('难度等级', default=1, 
                                   validators=[MinValueValidator(1), MaxValueValidator(5)],
                                   help_text='1-5级，1最简单，5最难') # integerfield 对应 int类型
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    is_active = models.BooleanField('是否启用', default=True)
    
    class Meta:
        verbose_name = '练习题目'
        verbose_name_plural = '练习题目'
        ordering = ['case', 'created_at']
    
    def get_options_list(self):
        """获取选项列表"""
        try:
            return json.loads(self.options)
        except json.JSONDecodeError:
            return []
    
    def set_options_list(self, options_list):
        """设置选项列表"""
        self.options = json.dumps(options_list, ensure_ascii=False)
    
    def __str__(self):
        return f"{self.case.title} - {self.question[:50]}..."


class Exam(models.Model):
    """考试模型"""
    EXAM_STATUSES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('in_progress', '进行中'),
        ('finished', '已结束'),
        ('cancelled', '已取消'),
    ]
    
    title = models.CharField('考试标题', max_length=200)
    description = models.TextField('考试说明', blank=True, help_text='考试的详细说明和注意事项')
    exercises = models.ManyToManyField(Exercise, verbose_name='考试题目', 
                                      help_text='本次考试包含的题目')    # manytomanyfield 对应 多对多关系
    start_time = models.DateTimeField('开始时间', help_text='考试开始的具体时间')
    duration = models.IntegerField('考试时长', help_text='考试持续时间，单位：分钟')
    total_score = models.DecimalField('总分', max_digits=5, decimal_places=2, default=100.00) # decimalfield 对应 float类型
    pass_score = models.DecimalField('及格分', max_digits=5, decimal_places=2, default=60.00)
    status = models.CharField('考试状态', max_length=20, choices=EXAM_STATUSES, default='draft')
    participants = models.ManyToManyField(User, blank=True, verbose_name='参与学生',
                                          help_text='参与此次考试的学生，如果为空则所有学生都可参与')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_exams',
                                  verbose_name='创建者')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '考试'
        verbose_name_plural = '考试'
        ordering = ['-start_time']
    
    @property
    def end_time(self):
        """考试结束时间"""
        return self.start_time + timezone.timedelta(minutes=self.duration)
    
    @property
    def is_active(self):
        """考试是否正在进行"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time and self.status == 'published'
    
    @property
    def is_finished(self):
        """考试是否已结束"""
        return timezone.now() > self.end_time or self.status == 'finished'
    
    @property
    def can_start(self):
        """是否可以开始考试"""
        now = timezone.now()
        return self.start_time <= now and self.status == 'published'
    
    def get_questions_count(self):
        """获取题目数量"""
        return self.exercises.count()
    
    def auto_update_status(self):
        """自动更新考试状态"""
        now = timezone.now()
        if self.status == 'published':
            if now < self.start_time:
                pass  # 保持已发布状态
            elif self.start_time <= now <= self.end_time:
                self.status = 'in_progress'
                self.save()
            elif now > self.end_time:
                self.status = 'finished'
                self.save()
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class ExamRecord(models.Model):
    """考试记录模型"""
    EXAM_TYPES = [
        ('practice', '练习模式'),
        ('exam', '正式考试'),
        ('mock', '模拟考试'),
    ]
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='records',
                            verbose_name='关联考试', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_records',
                            verbose_name='用户')
    exam_type = models.CharField('考试类型', max_length=20, choices=EXAM_TYPES, default='exam')
    exercises = models.ManyToManyField(Exercise, verbose_name='关联练习题目',
                                      help_text='本次考试包含的题目')
    score = models.DecimalField('得分', max_digits=5, decimal_places=2, default=0.00,
                               validators=[MinValueValidator(0), MaxValueValidator(100)],
                               help_text='考试得分，满分100分')
    total_questions = models.IntegerField('题目总数', default=0)
    correct_answers = models.IntegerField('正确答案数', default=0)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    time_spent = models.IntegerField('用时（分钟）', default=0, help_text='考试用时，单位：分钟')
    is_completed = models.BooleanField('是否完成', default=False)
    is_passed = models.BooleanField('是否通过', default=False, help_text='是否达到及格分数线')
    
    class Meta:
        verbose_name = '考试记录'
        verbose_name_plural = '考试记录'
        ordering = ['-created_at']
    
    def calculate_score(self):
        """计算考试得分"""
        if self.total_questions > 0:
            self.score = (self.correct_answers / self.total_questions) * 100
        else:
            self.score = 0
        
        # 自动判断是否通过（假设60分及格）
        self.is_passed = self.score >= 60
        return self.score
    
    def calculate_time_spent(self):
        """计算考试用时"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.time_spent = int(delta.total_seconds() / 60)  # 转换为分钟
        return self.time_spent
    
    @property
    def accuracy(self):
        """获取正确率百分比"""
        if self.total_questions > 0:
            return round((self.correct_answers / self.total_questions) * 100, 2)
        return 0
    
    def __str__(self):
        exam_name = self.exam.title if self.exam else "练习模式"
        return f"{self.user.username} - {exam_name} - {self.score}分"


class UserProgress(models.Model):
    """用户进度模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress',
                               verbose_name='用户')
    completed_cases = models.ManyToManyField(Case, blank=True, verbose_name='完成的病例',
                                           help_text='用户已学习完成的病例')
    completed_exercises = models.ManyToManyField(Exercise, blank=True, verbose_name='完成的练习',
                                               help_text='用户已完成的练习题目')
    progress_percentage = models.DecimalField('进度百分比', max_digits=5, decimal_places=2, 
                                            default=0.00,
                                            validators=[MinValueValidator(0), MaxValueValidator(100)],
                                            help_text='学习进度百分比')
    total_study_time = models.IntegerField('总学习时长', default=0, help_text='总学习时长，单位：分钟')
    last_study_date = models.DateTimeField('最后学习时间', auto_now=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '用户进度'
        verbose_name_plural = '用户进度'
    
    def update_progress(self):
        """更新学习进度"""
        total_cases = Case.objects.filter(is_active=True).count()
        completed_cases_count = self.completed_cases.filter(is_active=True).count()
        
        if total_cases > 0:
            self.progress_percentage = (completed_cases_count / total_cases) * 100
        else:
            self.progress_percentage = 0
        
        self.save()
        return self.progress_percentage
    
    def get_exam_stats(self):
        """获取考试统计数据"""
        exam_records = ExamRecord.objects.filter(user=self.user, is_completed=True)
        total_exams = exam_records.count()
        passed_exams = exam_records.filter(is_passed=True).count()
        avg_score = exam_records.aggregate(avg=models.Avg('score'))['avg'] or 0
        
        return {
            'total_exams': total_exams,
            'passed_exams': passed_exams,
            'pass_rate': round((passed_exams / total_exams * 100), 2) if total_exams > 0 else 0,
            'avg_score': round(avg_score, 2)
        }
    
    def __str__(self):
        return f"{self.user.username} - 进度: {self.progress_percentage}%"


class UserAnswer(models.Model):
    """用户答题记录模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers',
                            verbose_name='用户')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='user_answers',
                               verbose_name='题目')
    exam_record = models.ForeignKey(ExamRecord, on_delete=models.CASCADE, 
                                   related_name='answers', verbose_name='考试记录',
                                   blank=True, null=True)
    user_answer = models.CharField('用户答案', max_length=50)
    is_correct = models.BooleanField('是否正确', default=False)
    answer_time = models.DateTimeField('答题时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '用户答题记录'
        verbose_name_plural = '用户答题记录'
        unique_together = ['user', 'exercise', 'exam_record']  # 避免重复答题
    
    def check_answer(self):
        """检查答案是否正确"""
        self.is_correct = (self.user_answer.upper() == self.exercise.correct_answer.upper())
        return self.is_correct
    
    def __str__(self):
        return f"{self.user.username} - {self.exercise.question[:30]}... - {'正确' if self.is_correct else '错误'}"


class ExamResult(models.Model):
    """模拟考试结果模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_results',
                            verbose_name='学生')
    score = models.DecimalField('得分', max_digits=5, decimal_places=2, default=0.00,
                               validators=[MinValueValidator(0), MaxValueValidator(100)],
                               help_text='考试得分，满分100分')
    total_questions = models.IntegerField('题目总数', default=0)
    correct_answers = models.IntegerField('正确答案数', default=0)
    time_spent = models.IntegerField('考试用时', default=0, help_text='考试用时，单位：分钟')
    created_at = models.DateTimeField('完成时间', auto_now_add=True)
    questions = models.ManyToManyField(Exercise, verbose_name='考试题目',
                                     help_text='本次考试包含的题目')
    answers = models.TextField('答题记录', blank=True, help_text='JSON格式存储答题详情')
    
    class Meta:
        verbose_name = '模拟考试结果'
        verbose_name_plural = '模拟考试结果'
        ordering = ['-created_at']
    
    def calculate_score(self):
        """计算考试得分"""
        if self.total_questions > 0:
            self.score = (self.correct_answers / self.total_questions) * 100
        else:
            self.score = 0
        return self.score
    
    @property
    def accuracy(self):
        """获取正确率百分比"""
        if self.total_questions > 0:
            return round((self.correct_answers / self.total_questions) * 100, 2)
        return 0
    
    def __str__(self):
        return f"{self.user.username} - 模拟考试 - {self.score}分"


# ================== 临床推理教学系统模型 ==================

class ClinicalCase(models.Model):
    """
    临床案例模型 - 核心教学内容
    用于呈现真实的眼科临床案例，包含患者信息、主诉、现病史等
    """
    title = models.CharField(max_length=200, verbose_name="案例标题")
    case_id = models.CharField(max_length=50, unique=True, verbose_name="案例编号")
    
    # 患者基本信息
    patient_age = models.IntegerField(verbose_name="患者年龄")
    patient_gender = models.CharField(max_length=10, choices=[('M', '男'), ('F', '女')], verbose_name="患者性别")
    
    # 临床信息
    chief_complaint = models.TextField(verbose_name="主诉")
    present_illness = models.TextField(verbose_name="现病史")
    past_history = models.TextField(blank=True, verbose_name="既往史")
    family_history = models.TextField(blank=True, verbose_name="家族史")
    
    # 教学相关
    learning_objectives = models.JSONField(verbose_name="学习目标", help_text="JSON格式存储多个学习目标")
    difficulty_level = models.CharField(
        max_length=20, 
        choices=[('beginner', '初级'), ('intermediate', '中级'), ('advanced', '高级')],
        default='intermediate',
        verbose_name="难度等级"
    )
    
    # 案例状态
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 案例图片
    case_images = models.JSONField(blank=True, null=True, verbose_name="案例图片", help_text="存储图片路径的JSON数组")
    
    class Meta:
        verbose_name = "临床案例"
        verbose_name_plural = "临床案例"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.case_id} - {self.title}"


class ExaminationOption(models.Model):
    """
    检查选项模型 - 临床检查的可选项
    学生需要从中选择合适的检查项目来获取更多临床信息
    """
    clinical_case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='examination_options', verbose_name="关联案例")
    
    examination_type = models.CharField(
        max_length=50,
        choices=[
            ('basic', '基础检查'),
            ('imaging', '影像检查'),
            ('laboratory', '实验室检查'),
            ('special', '特殊检查'),
            ('fundus', '眼底检查')  # 新增眼底检查类型
        ],
        verbose_name="检查类型"
    )
    
    examination_name = models.CharField(max_length=100, verbose_name="检查名称")
    examination_description = models.TextField(verbose_name="检查描述")
    
    # 检查结果
    normal_result = models.TextField(verbose_name="正常结果描述")
    abnormal_result = models.TextField(blank=True, verbose_name="异常结果描述")
    actual_result = models.TextField(verbose_name="实际检查结果")
    
    # 教学价值
    diagnostic_value = models.IntegerField(
        choices=[(1, '低'), (2, '中'), (3, '高')],
        default=2,
        verbose_name="诊断价值"
    )
    cost_effectiveness = models.IntegerField(
        choices=[(1, '低'), (2, '中'), (3, '高')],
        default=2,
        verbose_name="成本效益"
    )
    
    # 检查相关图片/视频
    result_images = models.JSONField(blank=True, null=True, verbose_name="结果图片")
    
    # 新增字段：检查选择要求
    is_required = models.BooleanField(default=False, verbose_name="是否必选检查", 
                                    help_text="必选检查项必须被选择才能进入下一步")
    is_multiple_choice = models.BooleanField(default=False, verbose_name="是否允许多选")
    selection_group = models.CharField(max_length=50, blank=True, verbose_name="选择组",
                                     help_text="同组内的检查项可以一起选择")
    
    # 眼底检查特殊处理
    is_fundus_exam = models.BooleanField(default=False, verbose_name="是否眼底检查")
    fundus_reminder_text = models.CharField(
        max_length=200, 
        default="请移步旁边进行观察",
        verbose_name="眼底检查提示文字"
    )
    
    # 基础眼科检查特殊字段
    left_eye_vision = models.CharField(max_length=10, blank=True, verbose_name="左眼视力", 
                                     help_text="如：0.8, 1.0")
    right_eye_vision = models.CharField(max_length=10, blank=True, verbose_name="右眼视力",
                                      help_text="如：0.8, 1.0")
    left_eye_pressure = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, 
                                          verbose_name="左眼眼压 (mmHg)", help_text="正常范围：10-21")
    right_eye_pressure = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True,
                                           verbose_name="右眼眼压 (mmHg)", help_text="正常范围：10-21")
    
    # 影像检查图片（OCT和眼底照相）
    left_eye_image = models.ImageField(upload_to='examination_images/', blank=True, null=True,
                                     verbose_name="左眼检查图片", help_text="OCT或眼底照相的左眼图片")
    right_eye_image = models.ImageField(upload_to='examination_images/', blank=True, null=True,
                                      verbose_name="右眼检查图片", help_text="OCT或眼底照相的右眼图片")
    
    is_recommended = models.BooleanField(default=False, verbose_name="是否推荐检查")
    display_order = models.IntegerField(default=0, verbose_name="显示顺序")
    
    class Meta:
        verbose_name = "检查选项"
        verbose_name_plural = "检查选项"
        ordering = ['display_order', 'examination_type']
    
    def __str__(self):
        return f"{self.clinical_case.case_id} - {self.examination_name}"


class DiagnosisOption(models.Model):
    """
    诊断选项模型 - 鉴别诊断的候选项
    提供多个可能的诊断选项，学生需要根据临床信息进行判断
    """
    clinical_case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='diagnosis_options', verbose_name="关联案例")
    
    diagnosis_name = models.CharField(max_length=200, verbose_name="诊断名称")
    diagnosis_code = models.CharField(max_length=50, blank=True, verbose_name="诊断编码(ICD-10)")
    
    # 诊断相关性
    is_correct_diagnosis = models.BooleanField(default=False, verbose_name="是否正确诊断")
    is_differential = models.BooleanField(default=True, verbose_name="是否鉴别诊断")
    
    # 诊断依据
    supporting_evidence = models.TextField(verbose_name="支持依据")
    contradicting_evidence = models.TextField(blank=True, verbose_name="反对依据")
    
    # 诊断特征
    typical_symptoms = models.JSONField(verbose_name="典型症状", help_text="JSON格式存储症状列表")
    typical_signs = models.JSONField(verbose_name="典型体征", help_text="JSON格式存储体征列表")
    
    # 教学反馈
    correct_feedback = models.TextField(verbose_name="选择正确时的反馈")
    incorrect_feedback = models.TextField(verbose_name="选择错误时的反馈")
    
    probability_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="诊断概率分数"
    )
    
    display_order = models.IntegerField(default=0, verbose_name="显示顺序")
    
    class Meta:
        verbose_name = "诊断选项"
        verbose_name_plural = "诊断选项"
        ordering = ['display_order', '-probability_score']
    
    def __str__(self):
        return f"{self.clinical_case.case_id} - {self.diagnosis_name}"


class TreatmentOption(models.Model):
    """
    治疗选项模型 - 治疗方案的候选项
    基于诊断结果，提供相应的治疗选择
    """
    clinical_case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, related_name='treatment_options', verbose_name="关联案例")
    related_diagnosis = models.ForeignKey(DiagnosisOption, on_delete=models.CASCADE, blank=True, null=True, verbose_name="关联诊断")
    
    treatment_type = models.CharField(
        max_length=50,
        choices=[
            ('medication', '药物治疗'),
            ('surgery', '手术治疗'),
            ('observation', '观察等待'),
            ('referral', '转诊'),
            ('lifestyle', '生活方式干预'),
            ('combination', '综合治疗')
        ],
        verbose_name="治疗类型"
    )
    
    treatment_name = models.CharField(max_length=200, verbose_name="治疗方案名称")
    treatment_description = models.TextField(verbose_name="治疗方案描述")
    
    # 治疗评估
    is_optimal = models.BooleanField(default=False, verbose_name="是否最佳治疗")
    is_acceptable = models.BooleanField(default=True, verbose_name="是否可接受治疗")
    is_contraindicated = models.BooleanField(default=False, verbose_name="是否禁忌")
    
    # 治疗特性
    efficacy_score = models.IntegerField(
        choices=[(1, '低'), (2, '中'), (3, '高')],
        default=2,
        verbose_name="疗效评分"
    )
    safety_score = models.IntegerField(
        choices=[(1, '低'), (2, '中'), (3, '高')],
        default=2,
        verbose_name="安全性评分"
    )
    cost_score = models.IntegerField(
        choices=[(1, '低'), (2, '中'), (3, '高')],
        default=2,
        verbose_name="成本评分"
    )
    
    # 预期结果
    expected_outcome = models.TextField(verbose_name="预期疗效")
    potential_complications = models.TextField(blank=True, verbose_name="潜在并发症")
    
    # 教学反馈
    selection_feedback = models.TextField(verbose_name="选择该治疗时的反馈")
    
    display_order = models.IntegerField(default=0, verbose_name="显示顺序")
    
    class Meta:
        verbose_name = "治疗选项"
        verbose_name_plural = "治疗选项"
        ordering = ['display_order', '-efficacy_score']
    
    def __str__(self):
        return f"{self.clinical_case.case_id} - {self.treatment_name}"


class StudentClinicalSession(models.Model):
    """
    学生临床推理会话模型 - 跟踪学生的学习过程
    记录学生在特定案例中的完整学习轨迹
    """
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="学生")
    clinical_case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE, verbose_name="临床案例")
    
    # 会话状态 - 新的六步流程
    session_status = models.CharField(
        max_length=30,  # 增加长度以适应最长的选项
        choices=[
            ('case_presentation', '病例呈现'),         # 步骤1: 呈现病例
            ('examination_selection', '检查选择'),     # 步骤2: 选择检查方法
            ('examination_results', '检查结果'),       # 步骤3: 查看检查图像结果
            ('diagnosis_reasoning', '诊断推理'),       # 步骤4: 诊断判断推理
            ('treatment_selection', '治疗选择'),       # 步骤5: 选择治疗方案
            ('learning_feedback', '学习反馈'),         # 步骤6: 学习反馈
            ('completed', '已完成')
        ],
        default='case_presentation',
        verbose_name="当前阶段"
    )
    
    # 学习轨迹
    selected_examinations = models.JSONField(default=list, verbose_name="已选检查项目")
    examination_images_viewed = models.JSONField(default=list, verbose_name="已查看的检查图像")
    selected_diagnosis = models.ForeignKey(DiagnosisOption, on_delete=SET_NULL, blank=True, null=True, verbose_name="选择的诊断")
    diagnosis_reasoning_text = models.TextField(blank=True, verbose_name="诊断推理过程", 
                                               help_text="学生的诊断思路和推理过程")
    selected_treatments = models.JSONField(default=list, verbose_name="已选治疗方案")
    
    # 六步流程完成状态
    step_completion_status = models.JSONField(
        default=dict, 
        verbose_name="步骤完成状态",
        help_text="记录每个步骤的完成情况：{step_name: {completed: bool, score: float, completion_time: datetime}}"
    )
    
    # 检查选择验证
    required_examinations_completed = models.BooleanField(default=False, verbose_name="必选检查是否完成")
    examination_selection_valid = models.BooleanField(default=False, verbose_name="检查选择是否有效")
    
    # 学习评估
    examination_score = models.FloatField(default=0.0, verbose_name="检查选择得分")
    diagnosis_score = models.FloatField(default=0.0, verbose_name="诊断准确性得分")
    treatment_score = models.FloatField(default=0.0, verbose_name="治疗方案得分")
    reasoning_score = models.FloatField(default=0.0, verbose_name="推理过程得分")
    overall_score = models.FloatField(default=0.0, verbose_name="总体得分")
    
    # 时间跟踪
    time_spent = models.JSONField(default=dict, verbose_name="各阶段用时", help_text="JSON格式记录各阶段耗时")
    step_start_times = models.JSONField(default=dict, verbose_name="各步骤开始时间")
    
    # 会话记录
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="完成时间")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="最后活动时间")
    
    # 学习成果
    learning_notes = models.TextField(blank=True, verbose_name="学习笔记")
    reflection = models.TextField(blank=True, verbose_name="学习反思")
    
    class Meta:
        verbose_name = "学生临床会话"
        verbose_name_plural = "学生临床会话"
        ordering = ['-started_at']
        unique_together = ['student', 'clinical_case']
    
    def __str__(self):
        return f"{self.student.username} - {self.clinical_case.title} - {self.session_status}"
    
    def calculate_overall_score(self):
        """计算总体得分"""
        weights = {
            'examination': 0.3,  # 30%
            'diagnosis': 0.5,    # 50% (修正：原来是0.4)
            'treatment': 0.2     # 20% (修正：原来是0.3)
        }
        self.overall_score = (
            self.examination_score * weights['examination'] +
            self.diagnosis_score * weights['diagnosis'] +
            self.treatment_score * weights['treatment']
        )
        return self.overall_score


class TeachingFeedback(models.Model):
    """
    教学反馈模型 - 智能化教学指导
    为学生提供个性化的学习反馈和改进建议
    """
    student_session = models.ForeignKey(StudentClinicalSession, on_delete=models.CASCADE, related_name='feedbacks', verbose_name="学生会话")
    
    feedback_stage = models.CharField(
        max_length=20,
        choices=[
            ('examination', '检查阶段'),
            ('diagnosis', '诊断阶段'),
            ('treatment', '治疗阶段'),
            ('overall', '总体反馈')
        ],
        verbose_name="反馈阶段"
    )
    
    # 反馈内容
    feedback_type = models.CharField(
        max_length=20,
        choices=[
            ('positive', '积极反馈'),
            ('corrective', '纠正性反馈'),
            ('guidance', '指导性反馈'),
            ('encouragement', '鼓励性反馈')
        ],
        verbose_name="反馈类型"
    )
    
    feedback_content = models.TextField(verbose_name="反馈内容")
    improvement_suggestions = models.TextField(blank=True, verbose_name="改进建议")
    
    # 相关资源
    reference_materials = models.JSONField(blank=True, null=True, verbose_name="参考资料", help_text="相关学习资源链接")
    
    # 反馈元数据
    is_automated = models.BooleanField(default=True, verbose_name="是否自动生成")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "教学反馈"
        verbose_name_plural = "教学反馈"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student_session.student.username} - {self.feedback_stage} - {self.feedback_type}"
