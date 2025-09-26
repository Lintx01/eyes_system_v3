from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class Case(models.Model):
    """眼科病例模型"""
    title = models.CharField('病例名称', max_length=200, help_text='病例的标题或名称')
    description = models.TextField('病例描述', help_text='详细的病例描述和背景信息')
    symptoms = models.TextField('症状表现', help_text='患者的主要症状和表现')
    diagnosis = models.TextField('诊断结果', help_text='各项检查的详细结果', default='待补充')
    image = models.ImageField('病例图像', upload_to='case_images/', blank=True, null=True, 
                             help_text='相关的检查图片或眼底照片')
    difficulty = models.CharField('难度等级', max_length=10, 
                                 choices=[('easy', '简单'), ('medium', '中等'), ('hard', '困难')],
                                 default='medium', help_text='病例难度等级')
    case_type = models.CharField('病例类型', max_length=20,
                                choices=[('clinical', '临床病例'), ('surgery', '手术病例'), ('emergency', '急诊病例')],
                                default='clinical', help_text='病例类型分类')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    is_active = models.BooleanField('是否启用', default=True, help_text='是否在教学中使用此病例')
    
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
                            verbose_name='关联病例', help_text='此题目关联的病例')
    question = models.TextField('题干', help_text='题目的问题内容')
    question_type = models.CharField('题目类型', max_length=20, choices=QUESTION_TYPES, 
                                    default='single')
    options = models.TextField('选项', help_text='题目选项，JSON格式存储，如：["A选项", "B选项", "C选项", "D选项"]')
    correct_answer = models.CharField('正确答案', max_length=50, 
                             help_text='正确答案，单选填A/B/C/D，多选填AB/AC等，判断题填T/F')
    explanation = models.TextField('答案解析', blank=True, help_text='题目答案的详细解析')
    difficulty = models.IntegerField('难度等级', default=1, 
                                   validators=[MinValueValidator(1), MaxValueValidator(5)],
                                   help_text='1-5级，1最简单，5最难')
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
                                      help_text='本次考试包含的题目')
    start_time = models.DateTimeField('开始时间', help_text='考试开始的具体时间')
    duration = models.IntegerField('考试时长', help_text='考试持续时间，单位：分钟')
    total_score = models.DecimalField('总分', max_digits=5, decimal_places=2, default=100.00)
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
