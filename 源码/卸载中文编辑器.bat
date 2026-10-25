@echo off
title 卸载 中文编辑器 - 快捷方式与关联
echo ==========================================
echo    中文编辑器 卸载（快捷方式 + 文件关联）
echo ==========================================
echo.

rem ---- 1. 删除桌面快捷方式 ----
if exist "%USERPROFILE%\Desktop\中文编辑器.lnk" (
    del /q "%USERPROFILE%\Desktop\中文编辑器.lnk"
    echo [1/4] 已删除桌面快捷方式
) else (
    echo [1/4] 桌面快捷方式不存在，跳过
)

rem ---- 2. 删除开始菜单快捷方式 ----
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\中文编辑器.lnk" (
    del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\中文编辑器.lnk"
    echo [2/4] 已删除开始菜单快捷方式
) else (
    echo [2/4] 开始菜单快捷方式不存在，跳过
)

rem ---- 3. 删除 .cnpy 文件关联 ----
reg delete "HKCU\Software\Classes\.cnpy" /f >nul 2>&1
reg delete "HKCU\Software\Classes\CNEditor.cnpy" /f >nul 2>&1
echo [3/4] 已删除 .cnpy 文件关联

rem ---- 4. 删除控制面板卸载信息 ----
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\中文编辑器" /f >nul 2>&1
echo [4/4] 已删除控制面板卸载信息

echo.
echo ==========================================
echo   快捷方式和关联已清理完毕！
echo.
echo   程序文件请手动删除：
echo     打开安装目录，选中全部文件删除即可
echo   （默认安装目录：
echo     %LOCALAPPDATA%\Programs\中文编辑器）
echo ==========================================
echo.
pause
