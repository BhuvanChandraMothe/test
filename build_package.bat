@echo off
echo ========================================
echo Building SAP OData Connector Package
echo ========================================
echo.

REM Check if build tools are installed
pip show build >nul 2>&1
if errorlevel 1 (
    echo Installing build tools...
    pip install build twine
)

echo.
echo Cleaning old builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.egg-info rmdir /s /q *.egg-info

echo.
echo Building package...
python -m build

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Distribution files created in 'dist' folder:
dir dist
echo.
echo To install locally:
echo   pip install dist\sap_odata_connector-1.0.0-py3-none-any.whl
echo.
echo To install in development mode:
echo   pip install -e .
echo.
pause
