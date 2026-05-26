@echo off
echo 正在打包关键词TXT生成器到桌面...
echo.

cd /d "%~dp0"

python -m PyInstaller --onefile --windowed --name "关键词同名TXT生成工具v1.2.0" --icon "%~dp0assets\app.ico" --version-file "%~dp0version_info.txt" --distpath "%USERPROFILE%\Desktop" --workpath "build_pyinstaller" --specpath "build_pyinstaller" --add-data "%~dp0region_db.json;." --add-data "%~dp0assets\app.ico;assets/" main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 打包成功！可执行文件已保存到桌面: %USERPROFILE%\Desktop\关键词同名TXT生成工具v1.2.0.exe
) else (
    echo.
    echo 打包失败！请检查错误信息。
)

echo.
pause