@echo off
echo 正在打包关键词TXT生成器到桌面...
echo.

cd /d "%~dp0"

python -m PyInstaller --clean --onefile --windowed --name keyword_txt_generator --distpath "%USERPROFILE%\Desktop" --workpath "build_pyinstaller" --specpath "build_pyinstaller" --add-data "region_db.json;." main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 打包成功！可执行文件已保存到桌面: %USERPROFILE%\Desktop\keyword_txt_generator.exe
) else (
    echo.
    echo 打包失败！请检查错误信息。
)

echo.
pause