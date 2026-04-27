@echo off
setlocal

set PLUGIN_NAME=krita_ai_metadata
set DESKTOP_FILE=%PLUGIN_NAME%.desktop
set OUT_ZIP=%PLUGIN_NAME%.zip

cd /d "%~dp0"

if not exist "%PLUGIN_NAME%\" (
	echo ERROR: Missing plugin folder: %PLUGIN_NAME%\
	exit /b 1
)

if not exist "%DESKTOP_FILE%" (
	echo ERROR: Missing desktop file: %DESKTOP_FILE%
	exit /b 1
)

if exist "%OUT_ZIP%" del /f /q "%OUT_ZIP%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
	"$ErrorActionPreference = 'Stop';" ^
	"$plugin = '%PLUGIN_NAME%';" ^
	"$desktop = '%DESKTOP_FILE%';" ^
	"$out = '%OUT_ZIP%';" ^
	"$temp = Join-Path $PWD '.build_krita_ai_metadata_zip';" ^
	"if (Test-Path $temp) { Remove-Item $temp -Recurse -Force };" ^
	"New-Item -ItemType Directory -Path $temp | Out-Null;" ^
	"Copy-Item $desktop -Destination $temp;" ^
	"Copy-Item $plugin -Destination $temp -Recurse;" ^
	"Get-ChildItem $temp -Recurse -Force -Directory | Where-Object { $_.Name -in @('__pycache__','.pytest_cache','.mypy_cache','.ruff_cache') } | Remove-Item -Recurse -Force;" ^
	"Get-ChildItem $temp -Recurse -Force -File | Where-Object { $_.Extension -in @('.pyc','.pyo','.pyd','.log','.tmp','.bak') } | Remove-Item -Force;" ^
	"Compress-Archive -Path (Join-Path $temp '*') -DestinationPath $out -Force;" ^
	"Remove-Item $temp -Recurse -Force;" ^
	"Write-Host \"Built $out\";" ^
	"Write-Host 'ZIP root contains:';" ^
	"Write-Host \"- $plugin/\";" ^
	"Write-Host \"- $desktop\";"

if errorlevel 1 (
	echo ERROR: Build failed.
	exit /b 1
)

endlocal