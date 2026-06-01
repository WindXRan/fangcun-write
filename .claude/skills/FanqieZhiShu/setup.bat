@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ============================================================
:: 番茄指数 - 一键启动脚本
:: 自动检测环境、安装依赖、引导配置、运行项目
:: ============================================================

title 番茄指数 - 一键启动

:MAIN_MENU
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║           番茄指数 FanqieRankTracker - 一键启动          ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║                                                          ║
echo  ║   [1] 首次安装（安装依赖 + 配置环境）                    ║
echo  ║   [2] 运行爬虫（抓取今日数据）                          ║
echo  ║   [3] 构建看板（生成趋势分析）                          ║
echo  ║   [4] 启动预览（本地打开看板）                          ║
echo  ║   [5] 完整流程（爬虫 + 构建 + 预览）                    ║
echo  ║   [6] 配置 AI 服务                                      ║
echo  ║   [0] 退出                                              ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

set /p choice="请选择操作 [0-6]: "

if "%choice%"=="1" goto INSTALL
if "%choice%"=="2" goto SCRAPE
if "%choice%"=="3" goto BUILD
if "%choice%"=="4" goto PREVIEW
if "%choice%"=="5" goto FULL_RUN
if "%choice%"=="6" goto CONFIG_AI
if "%choice%"=="0" goto EXIT
echo 无效选择，请重新输入。
timeout /t 2 >nul
goto MAIN_MENU

:: ============================================================
:: 1. 首次安装
:: ============================================================
:INSTALL
cls
echo.
echo  ========================================
echo   步骤 1/4：检查 Python 环境
echo  ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [错误] 未检测到 Python！
    echo.
    echo  请先安装 Python 3.10 或更高版本：
    echo  下载地址：https://www.python.org/downloads/
    echo.
    echo  安装时请勾选 "Add Python to PATH"
    echo.
    pause
    goto MAIN_MENU
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] Python 版本：%PYVER%

echo.
echo  ========================================
echo   步骤 2/4：检测依赖环境
echo  ========================================
echo.

:: 检测全局环境是否已有依赖
set "USE_VENV=1"
set "DEPS_OK=0"

python -c "import playwright; import openai" >nul 2>&1
if not errorlevel 1 (
    echo  [检测] 全局环境已安装所需依赖
    echo.
    echo  请选择安装方式：
    echo    [1] 使用全局环境（推荐，已有依赖可直接使用）
    echo    [2] 创建独立虚拟环境（隔离依赖）
    echo.
    set /p env_choice="请选择 [1/2]: "
    if "!env_choice!"=="1" (
        set "USE_VENV=0"
        set "DEPS_OK=1"
        echo  [OK] 将使用全局环境
    )
)

if "!USE_VENV!"=="1" (
    if not exist "venv" (
        echo  正在创建虚拟环境...
        python -m venv venv
        if errorlevel 1 (
            echo  [错误] 创建虚拟环境失败！
            pause
            goto MAIN_MENU
        )
        echo  [OK] 虚拟环境创建成功
    ) else (
        echo  [OK] 虚拟环境已存在
    )
    echo  正在激活虚拟环境...
    call venv\Scripts\activate.bat
)

if "!DEPS_OK!"=="0" (
    echo  正在安装 Python 依赖...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo  [错误] 安装依赖失败！
        pause
        goto MAIN_MENU
    )
    echo  [OK] Python 依赖安装完成
) else (
    echo  [OK] 依赖已就绪，跳过安装
)

echo.
echo  ========================================
echo   步骤 3/4：检查 Playwright 浏览器
echo  ========================================
echo.

:: 检测 Chromium 是否已安装
set "BROWSERS_DIR=%LOCALAPPDATA%\ms-playwright"
set "CHROMIUM_OK=0"

if exist "%BROWSERS_DIR%\chromium*" (
    echo  [检测] Playwright Chromium 浏览器已安装
    set "CHROMIUM_OK=1"
) else (
    echo  [检测] 未找到 Playwright Chromium 浏览器
)

if "!CHROMIUM_OK!"=="0" (
    echo  正在安装 Chromium 浏览器（首次需要下载，请耐心等待）...
    playwright install chromium
    if errorlevel 1 (
        echo  [错误] 安装 Playwright 浏览器失败！
        echo  请检查网络连接后重试。
        pause
        goto MAIN_MENU
    )
    echo  [OK] Playwright 浏览器安装完成
) else (
    echo  [OK] Playwright 浏览器已就绪，跳过安装
)

echo.
echo  ========================================
echo   步骤 4/4：配置 AI 服务（可选）
echo  ========================================
echo.
echo  AI 服务用于生成智能趋势分析摘要。
echo  不配置也可以正常使用，系统会使用规则摘要替代。
echo.
echo  是否现在配置 AI 服务？
echo  [1] 是，现在配置
echo  [2] 跳过，稍后配置
echo.
set /p ai_choice="请选择 [1/2]: "

if "%ai_choice%"=="1" goto CONFIG_AI

echo.
echo  ========================================
echo   安装完成！
echo  ========================================
echo.
echo  接下来您可以：
echo    - 运行爬虫：选择菜单 [2]
echo    - 构建看板：选择菜单 [3]
echo    - 启动预览：选择菜单 [4]
echo    - 完整流程：选择菜单 [5]（推荐新手使用）
echo.
pause
goto MAIN_MENU

:: ============================================================
:: 2. 运行爬虫
:: ============================================================
:SCRAPE
cls
echo.
echo  ========================================
echo   运行爬虫 - 抓取今日数据
echo  ========================================
echo.
echo  爬虫将抓取番茄小说四大榜单（女频新书/阅读、男频新书/阅读）
echo  每个分类 Top 30 本书，预计耗时 10-15 分钟。
echo.
echo  提示：爬虫运行期间请勿关闭窗口。
echo.
set /p confirm="确认开始？[Y/N]: "
if /i not "%confirm%"=="Y" goto MAIN_MENU

if exist "venv" (
    echo  正在激活虚拟环境...
    call venv\Scripts\activate.bat
)

echo  正在启动爬虫...
echo.
python scrape_fanqie_ranks.py

echo.
if errorlevel 1 (
    echo  [错误] 爬虫运行出错！请检查上方错误信息。
) else (
    echo  [OK] 爬虫运行完成！数据已保存到 data/ 目录。
)
echo.
pause
goto MAIN_MENU

:: ============================================================
:: 3. 构建看板
:: ============================================================
:BUILD
cls
echo.
echo  ========================================
echo   构建看板 - 生成趋势分析数据
echo  ========================================
echo.
if exist "venv" (
    echo  正在激活虚拟环境...
    call venv\Scripts\activate.bat
)

echo  正在构建看板数据...
echo.
python scripts/build_latest.py

echo.
if errorlevel 1 (
    echo  [错误] 构建出错！请检查上方错误信息。
) else (
    echo  [OK] 看板数据构建完成！
)
echo.
pause
goto MAIN_MENU

:: ============================================================
:: 4. 启动预览
:: ============================================================
:PREVIEW
cls
echo.
echo  ========================================
echo   启动预览 - 本地打开看板
echo  ========================================
echo.
echo  正在启动本地服务器...
echo  浏览器将自动打开 http://localhost:8000
echo.
echo  提示：按 Ctrl+C 可停止服务器。
echo.

:: 自动打开浏览器
start "" "http://localhost:8000"

:: 启动服务器
python -m http.server 8000

echo.
echo  服务器已停止。
pause
goto MAIN_MENU

:: ============================================================
:: 5. 完整流程
:: ============================================================
:FULL_RUN
cls
echo.
echo  ========================================
echo   完整流程 - 爬虫 + 构建 + 预览
echo  ========================================
echo.
echo  将依次执行：
echo    1. 运行爬虫（10-15 分钟）
echo    2. 构建看板数据
echo    3. 启动本地预览
echo.
set /p confirm="确认开始？[Y/N]: "
if /i not "%confirm%"=="Y" goto MAIN_MENU

echo.
echo  [1/3] 运行爬虫...
echo  ----------------------------------------
if exist "venv" (
    call venv\Scripts\activate.bat
)
python scrape_fanqie_ranks.py

if errorlevel 1 (
    echo.
    echo  [错误] 爬虫运行出错！
    pause
    goto MAIN_MENU
)

echo.
echo  [2/3] 构建看板数据...
echo  ----------------------------------------
python scripts/build_latest.py

if errorlevel 1 (
    echo.
    echo  [错误] 构建出错！
    pause
    goto MAIN_MENU
)

echo.
echo  [3/3] 启动本地预览...
echo  ----------------------------------------
echo.
echo  看板地址：http://localhost:8000
echo  按 Ctrl+C 可停止服务器。
echo.
start "" "http://localhost:8000"
python -m http.server 8000

echo.
echo  服务器已停止。
pause
goto MAIN_MENU

:: ============================================================
:: 6. 配置 AI 服务
:: ============================================================
:CONFIG_AI
cls
echo.
echo  ========================================
echo   配置 AI 服务
echo  ========================================
echo.
echo  支持任何 OpenAI 兼容 API，包括：
echo    - OpenAI（GPT-4o-mini 等）
echo    - DeepSeek
echo    - Moonshot（月之暗面）
echo    - 硅基流动 SiliconFlow
echo    - 本地 Ollama
echo    - 其他 OpenAI 兼容服务
echo.
echo  ----------------------------------------
echo.

:: 读取现有配置
set "CURRENT_BASE_URL="
set "CURRENT_API_KEY="
set "CURRENT_API_MODEL="

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if "%%a"=="API_BASE_URL" set "CURRENT_BASE_URL=%%b"
        if "%%a"=="API_KEY" set "CURRENT_API_KEY=%%b"
        if "%%a"=="API_MODEL" set "CURRENT_API_MODEL=%%b"
    )
)

if defined CURRENT_BASE_URL (
    echo  当前配置：
    echo    API_BASE_URL = %CURRENT_BASE_URL%
    echo    API_KEY = %CURRENT_API_KEY:~0,8%...
    echo    API_MODEL = %CURRENT_API_MODEL%
    echo.
)

echo  请输入 API 配置（直接回车跳过保持现有值）：
echo.

set /p "NEW_BASE_URL=  API_BASE_URL（如 https://api.deepseek.com/v1）: "
if "%NEW_BASE_URL%"=="" set "NEW_BASE_URL=%CURRENT_BASE_URL%"

set /p "NEW_API_KEY=  API_KEY: "
if "%NEW_API_KEY%"=="" set "NEW_API_KEY=%CURRENT_API_KEY%"

set /p "NEW_API_MODEL=  API_MODEL（如 deepseek-chat）: "
if "%NEW_API_MODEL%"=="" set "NEW_API_MODEL=%CURRENT_API_MODEL%"

:: 保存到 .env 文件
(
echo API_BASE_URL=%NEW_BASE_URL%
echo API_KEY=%NEW_API_KEY%
echo API_MODEL=%NEW_API_MODEL%
) > .env

echo.
echo  [OK] 配置已保存到 .env 文件
echo.
echo  提示：运行构建脚本时会自动读取 .env 配置。
echo  如果需要在前端使用 AI 功能，请在网页中点击齿轮图标配置。
echo.
pause
goto MAIN_MENU

:: ============================================================
:: 退出
:: ============================================================
:EXIT
echo.
echo  感谢使用番茄指数！再见！
echo.
exit /b 0
