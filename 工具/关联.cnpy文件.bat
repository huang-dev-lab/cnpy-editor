@echo off
rem ============================================
rem  中文编辑器 —— 一键关联 .cnpy 文件
rem  让 .cnpy 双击用中文编辑器打开，并显示编辑器图标
rem  （写入当前用户注册表，无需管理员权限；路径写死为本文件所在目录的 dist\中文编辑器.exe）
rem ============================================
chcp 65001>nul
setlocal

set "BASE=%~dp0"
set "EXE=%BASE%dist\中文编辑器.exe"
set "PROG=CNEditor.cnpy"

if not exist "%EXE%" (
    echo [错误] 找不到 %EXE%
    echo        请确认已经打包出 exe（dist 目录下有 中文编辑器.exe）。
    pause
    exit /b 1
)

reg add "HKCU\Software\Classes\.cnpy" /ve /d "%PROG%" /f >nul
reg add "HKCU\Software\Classes\%PROG%" /ve /d "中文编辑器文件" /f >nul
reg add "HKCU\Software\Classes\%PROG%\DefaultIcon" /ve /d "\"%EXE%\",0" /f >nul
reg add "HKCU\Software\Classes\%PROG%\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f >nul

rem 刷新图标缓存（Win10 用 -show 重载）
ie4uinit.exe -show >nul 2>&1

echo.
echo [完成] .cnpy 文件已关联到：%EXE%
echo        现在双击 .cnpy 文件就会用中文编辑器打开，图标也换好了。
echo        如果桌面图标没立刻刷新，注销或重启一次即可。
echo.
pause
