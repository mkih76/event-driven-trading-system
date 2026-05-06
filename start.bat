@echo off
chcp 65001 >nul
echo ==========================================
echo  事件驱动交易分析系统 - 启动脚本
echo ==========================================
echo.

cd /d C:\Users\22975\event-trading-system

echo [1/3] 正在启动 Docker Desktop...
echo     请确保 Docker Desktop 已在运行
echo.

echo [2/3] 正在构建并启动服务...
docker compose up -d --build

echo.
echo [3/3] 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
echo ==========================================
echo  服务已启动！
echo ==========================================
echo  前端界面: http://localhost:3000
echo  后端 API: http://localhost:8080
echo  API 文档: http://localhost:8080/docs
echo ==========================================
echo.
echo 查看日志: docker compose logs -f
echo 停止服务: docker compose down
echo.
pause
