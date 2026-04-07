@echo off
cd /d E:\pycharm\stock-analysis

echo ========================================
echo 全流程测试 - 数据同步 + 信号计算 + 报告生成
echo ========================================
echo.

echo [步骤1] 数据同步...
echo.
python main.py sync --index-only
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 数据同步失败！
    pause
    exit /b 1
)
echo [OK] 数据同步完成！
echo.

echo [步骤2] 计算买卖信号...
echo.
python main.py signal
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 信号计算失败！
    pause
    exit /b 1
)
echo [OK] 信号计算完成！
echo.

echo [步骤3] 生成报告...
echo.
python active_skills/stock_signal_generator/position_advisor.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 报告生成失败！
    pause
    exit /b 1
)
echo [OK] 报告生成完成！
echo.

echo [步骤4] 邮件推送...
echo.
echo （需要配置邮件客户端）
echo [OK] 邮件推送需配置SMTP账号
echo.

echo ========================================
echo 全流程测试完成！
echo ========================================
pause
