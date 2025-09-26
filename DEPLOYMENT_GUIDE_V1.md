# 眼科教学系统 v1.0 - 部署指南

## 📦 系统要求

### 基础环境
- **操作系统：** Windows 10/11, macOS 10.14+, Linux Ubuntu 18.04+
- **Python 版本：** Python 3.8 或更高版本
- **数据库：** SQLite 3（内置）
- **浏览器：** Chrome 70+, Firefox 65+, Safari 12+, Edge 79+

### Python 依赖包
```
Django==4.2.24
xlsxwriter>=3.0.0
```

## 🚀 快速部署

### 1. 环境准备
```bash
# 检查Python版本
python --version  # 确保 >= 3.8

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. 安装依赖
```bash
# 安装Django和相关依赖
pip install django xlsxwriter
```

### 3. 项目初始化
```bash
# 进入项目目录
cd eyessystem/system

# 执行数据库迁移
python manage.py migrate

# 创建管理员账户
python manage.py createsuperuser

# 初始化系统数据（用户组、示例数据）
python manage.py init_system
```

### 4. 启动服务
```bash
# 启动开发服务器
python manage.py runserver

# 访问系统
# 主页: http://127.0.0.1:8000
# 管理后台: http://127.0.0.1:8000/admin/
```

## 👥 用户账户设置

### 创建用户组
系统会自动创建以下用户组：
- **Teachers** - 教师组
- **Students** - 学生组

### 创建测试账户
```bash
# 进入Django Shell
python manage.py shell

# 创建测试教师账户
from django.contrib.auth.models import User, Group
teacher_group = Group.objects.get(name='Teachers')
teacher = User.objects.create_user('teacher1', 'teacher@example.com', 'password123')
teacher.groups.add(teacher_group)

# 创建测试学生账户
student_group = Group.objects.get(name='Students')
student = User.objects.create_user('student1', 'student@example.com', 'password123')
student.groups.add(student_group)
```

## 🔍 功能测试清单

### 学生功能测试：
- [ ] 用户登录和权限验证
- [ ] 病例学习功能
- [ ] 练习系统使用
- [ ] 正式考试参与
- [ ] 模拟考试功能
- [ ] 学习进度查看
- [ ] 成绩查看和分析

### 教师功能测试：
- [ ] 教师登录和权限验证
- [ ] 病例管理功能
- [ ] 题库管理功能
- [ ] 考试创建和管理
- [ ] 学生进度查看
- [ ] 数据统计和导出
- [ ] 成绩分析功能

### 系统功能测试：
- [ ] 自动评分算法
- [ ] 考试时间控制
- [ ] 权限控制机制
- [ ] 数据统计准确性
- [ ] 文件上传和下载

## 🔧 常见问题解决

### 问题 1: 启动时报错 "ModuleNotFoundError: No module named 'django'"
**解决方案：**
```bash
# 确保在虚拟环境中
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 重新安装Django
pip install django xlsxwriter
```

### 问题 2: 数据库迁移错误
**解决方案：**
```bash
# 删除迁移文件（保留__init__.py）
rm cases/migrations/0*.py

# 重新生成迁移
python manage.py makemigrations cases
python manage.py migrate
```

### 问题 3: 权限问题
**解决方案：**
```bash
# 重新运行初始化命令
python manage.py init_system

# 手动添加用户到组
python manage.py shell
>>> from django.contrib.auth.models import User, Group
>>> user = User.objects.get(username='username')
>>> group = Group.objects.get(name='Students')  # 或 'Teachers'
>>> user.groups.add(group)
```

### 问题 4: Timezone 错误
**解决方案：**
系统已修复timezone相关错误，如遇到问题请检查：
- Django版本是否为4.2.24
- Python版本是否支持datetime.timezone
- 时区设置是否正确

## 📊 数据备份

### 备份数据库
```bash
# SQLite备份
copy db.sqlite3 backup_%date:~0,8%_%time:~0,2%%time:~3,2%.sqlite3  # Windows
cp db.sqlite3 backup_$(date +%Y%m%d_%H%M%S).sqlite3  # Linux/macOS

# 导出数据
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
```

### 恢复数据库
```bash
# 从备份恢复
python manage.py loaddata backup_20240926_123456.json
```

## 🛡️ 安全建议

1. **更改默认密码**
   - 管理员账户使用强密码
   - 定期更换密码

2. **生产环境配置**
   - 设置DEBUG = False
   - 配置ALLOWED_HOSTS
   - 使用HTTPS

3. **权限管理**
   - 定期检查用户权限
   - 及时删除无效账户

## 📈 系统维护

### 定期清理：
```bash
# 清理过期的考试记录（可选）
python manage.py shell -c "
from cases.models import ExamRecord
from datetime import datetime, timedelta
from django.utils import timezone

# 删除6个月前的考试记录（根据需要调整）
cutoff_date = timezone.now() - timedelta(days=180)
old_records = ExamRecord.objects.filter(created_at__lt=cutoff_date)
print(f'将删除 {old_records.count()} 条过期记录')
# old_records.delete()  # 取消注释以执行删除
"
```

### 性能监控：
- 定期检查数据库大小
- 监控系统响应时间
- 关注用户活跃度统计

## 📞 技术支持

如遇到部署问题，请检查：
1. Python版本兼容性
2. 依赖包安装完整性
3. 数据库权限设置
4. 静态文件路径配置
5. 用户组和权限设置

## 🎉 部署完成检查

部署完成后，请确认以下功能正常：

### ✅ 基础功能
- [ ] 系统能正常启动
- [ ] 登录页面可以访问
- [ ] 管理员后台可以使用
- [ ] 静态文件正常加载

### ✅ 用户功能
- [ ] 教师可以正常登录并访问教师端
- [ ] 学生可以正常登录并访问学生端
- [ ] 权限控制正常工作

### ✅ 核心功能
- [ ] 病例学习功能正常
- [ ] 练习系统可以使用
- [ ] 考试功能完整可用
- [ ] 模拟考试功能正常
- [ ] 学生进度查看正常
- [ ] 数据导出功能可用

---

**版本：** v1.0  
**更新时间：** 2024年09月26日  
**适用系统：** 眼科教学系统 v1.0  

🎊 **恭喜！眼科教学系统 v1.0 部署完成！**