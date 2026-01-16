@echo off
REM 启动 API 服务器并将日志输出到文件
echo Starting API server with logging...
python -u api_server.py > api_server_log.txt 2>&1
