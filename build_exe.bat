@echo off
setlocal

cd /d "%~dp0"

echo [1/3] Installing/upgrading PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

echo [2/3] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ntn_efs_generator.spec del /q ntn_efs_generator.spec

rem If a local .\upx\ folder (containing upx.exe) exists, PyInstaller will use it
rem to compress the bundled DLLs/EXE. Download UPX from https://github.com/upx/upx/releases
rem and extract it into a "upx" folder next to this script to enable this.
set "UPX_ARGS="
if exist "%~dp0upx\upx.exe" (
    echo Found local UPX, enabling compression.
    set "UPX_ARGS=--upx-dir "%~dp0upx""
)

echo [3/3] Building single-file Windows executable...
python -m PyInstaller --noconfirm --onefile --windowed %UPX_ARGS% ^
    --exclude-module unittest --exclude-module pydoc --exclude-module doctest ^
    --exclude-module distutils --exclude-module xmlrpc --exclude-module email ^
    --exclude-module http --exclude-module multiprocessing --exclude-module sqlite3 ^
    --name ntn_efs_generator ntn_efs_generator.py
if errorlevel 1 goto :error

echo.
echo Build succeeded. Executable is at dist\ntn_efs_generator.exe
for %%F in (dist\ntn_efs_generator.exe) do echo Size: %%~zF bytes
goto :eof

:error
echo.
echo Build failed. See the errors above.
exit /b 1

