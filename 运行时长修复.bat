@echo off
echo ========================================
echo 学习时长数据修复工具
echo ========================================
echo.

cd /d "%~dp0"
cd eyessystem\system

echo 激活虚拟环境...
call conda activate med_train

echo.
echo 运行数据修复脚本...
python fix_study_time.py

echo.
echo ========================================
echo 修复完成！
echo ========================================
echo.
pause
