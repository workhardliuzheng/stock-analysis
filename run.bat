@echo off
chcp 65001 > nul
echo [OK] 启动A股投资顾问系统...
echo [OK] 使用虚拟环境: E:\copaw\.venv
E:\copaw\.venv\Scripts\python.exe %*
