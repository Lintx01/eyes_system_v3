@echo off
echo ======================================
echo 眼科教学系统 - 服务器启动脚本
echo ======================================
echo.

echo [1/3] 激活 Conda 环境...
call conda activate med_train
if %errorlevel% neq 0 (
    echo 错误: 无法激活 med_train 环境
    pause
    exit /b 1
)
echo ✓ 环境激活成功
echo.

echo [2/3] 切换到项目目录...
cd /d "%~dp0eyessystem\system"
if %errorlevel% neq 0 (
    echo 错误: 无法切换到项目目录
    pause
    exit /b 1
)
echo ✓ 目录切换成功: %CD%
echo.

echo [3/3] 启动 Django 服务器...
echo 提示: 按 Ctrl+C 可以停止服务器
echo 访问地址: http://127.0.0.1:8000/system/users/
echo.
python manage.py runserver
pause
