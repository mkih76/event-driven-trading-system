@echo off
chcp 65001 >nul
echo ========================================
echo 事件驱动交易分析系统 - 快速诊断
echo ========================================
echo.

echo [1/3] 检查 Docker 容器状态...
"D:\Docker\cli\resources\bin\docker.exe" ps
echo.

echo [2/3] 检查后端日志 (最后 20 行)...
"D:\Docker\cli\resources\bin\docker.exe" compose logs backend --tail 20
echo.

echo [3/3] 检查前端日志 (最后 10 行)...
"D:\Docker\cli\resources\bin\docker.exe" compose logs frontend --tail 10
echo.

echo ========================================
echo 诊断完成
echo ========================================
pause