@echo off
:: 根据你的搜索结果，docker 的资源文件都在 resources 目录下
set DOCKER_BIN="D:\Docker\cli\resources\bin\docker.exe"

if exist %DOCKER_BIN% (
    %DOCKER_BIN% compose up -d
    echo --------------------------------------------------
    echo [成功] 指令已发送！请查看 Docker Desktop 界面。
    echo --------------------------------------------------
) else (
    echo [路径排查] 找不到 docker.exe。
    echo 请检查 D:\Docker\cli\resources 文件夹下是否有 bin 文件夹，
    echo 以及 bin 文件夹内是否有 docker.exe。
)

pause