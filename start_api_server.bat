@echo off
REM 微信公众号文章API服务启动脚本 (Windows版本)
echo ========================================
echo 微信公众号文章API服务
echo ========================================

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3
    pause
    exit /b 1
)

REM 检查依赖
echo.
echo 📦 检查依赖...
set MISSING_DEPS=0

REM 检查Flask
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  缺少依赖: flask
    set MISSING_DEPS=1
)

REM 检查pywinauto
python -c "import pywinauto" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  缺少依赖: pywinauto
    set MISSING_DEPS=1
)

REM 检查pyperclip
python -c "import pyperclip" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  缺少依赖: pyperclip
    set MISSING_DEPS=1
)

if %MISSING_DEPS% neq 0 (
    echo.
    echo ❌ 缺少必要的依赖包
    echo.
    echo 是否现在安装？(y/n)
    set /p install_choice=
    
    if /i "%install_choice%"=="y" (
        echo.
        echo 📥 安装依赖...
        pip install -r requirements.txt
        
        if %errorlevel% neq 0 (
            echo ❌ 依赖安装失败
            pause
            exit /b 1
        )
        
        echo ✅ 依赖安装成功
    ) else (
        echo ❌ 请手动安装依赖: pip install -r requirements.txt
        pause
        exit /b 1
    )
) else (
    echo ✅ 所有依赖已安装
)

REM 检查微信是否运行
echo.
echo 🔍 检查微信状态...
tasklist /FI "IMAGENAME eq WeChat.exe" 2>NUL | find /I "WeChat.exe" >NUL
if %errorlevel% neq 0 (
    echo ⚠️  微信未运行
    echo.
    echo 是否现在启动微信？(y/n)
    set /p wechat_choice=
    
    if /i "%wechat_choice%"=="y" (
        echo 🚀 启动微信...
        start "" "C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"
        echo ⏳ 等待微信启动...
        timeout /t 3 >nul
    ) else (
        echo ⚠️  请手动启动微信并登录
    )
) else (
    echo ✅ 微信正在运行
)

REM 创建必要的目录
echo.
echo 📁 创建必要的目录...
if not exist "params" mkdir params
if not exist "articles_html" mkdir articles_html
echo ✅ 目录创建完成

REM 启动API服务器
echo.
echo ========================================
echo 🚀 启动API服务器...
echo ========================================
echo.
echo 服务地址: http://localhost:5000
echo.
echo API端点:
echo   - GET  /api/health         健康检查
echo   - POST /api/fetch_article  获取单篇文章
echo   - POST /api/fetch_articles 批量获取文章
echo   - POST /api/stop_proxy     停止代理服务器
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

REM 启动服务器
python api_server.py