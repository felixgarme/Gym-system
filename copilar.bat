@echo off
taskkill /f /im main.exe 2>nul
taskkill /f /im pantalla.exe 2>nul

echo === Compilando main.py ===
py -m nuitka --onefile --disable-console --enable-plugin=numpy --enable-plugin=tk-inter --include-package-data=face_recognition_models --include-package-data=ttkbootstrap --windows-icon-from-ico=icono.ico main.py

echo.
echo === Compilando pantalla.py ===
@REM py -m nuitka --onefile --disable-console pantalla.py

echo.
echo === Proceso finalizado ===
pause