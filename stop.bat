@echo off
chcp 65001 >nul
echo ==========================================
echo  事件驱动交易分析系统 - 停止脚本
echo ==========================================
echo.

cd /d C:\Users\22975\event-trading-system

echo 正在停止服务...
docker compose down

echo.
echo 服务已停止！
pause
