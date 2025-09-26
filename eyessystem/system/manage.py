#!/usr/bin/env python
"""Django的命令行管理工具 - 眼科教学软件系统"""
import os
import sys


def main():
    """运行Django管理任务的主函数"""
    # 设置默认的Django设置模块为eyehospital.settings
    # 如果环境变量中没有设置DJANGO_SETTINGS_MODULE，则使用默认值
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eyehospital.settings")
    
    try:
        # 导入Django的命令行执行函数
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # 如果导入失败，说明Django没有正确安装或环境配置有问题
        raise ImportError(
            "无法导入Django。请确保Django已正确安装并且 "
            "在PYTHONPATH环境变量中可用。是否忘记激活虚拟环境？"
        ) from exc
    
    # 执行命令行传入的Django管理命令
    # sys.argv包含了从命令行传入的所有参数
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    # 当脚本作为主程序运行时，调用main函数
    # 这是Python脚本的标准入口点写法
    main()
