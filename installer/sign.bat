@echo off
rem Firma BC-Transporter.exe + Setup con certificato code signing (OV/EV).
rem Richiede signtool (Windows SDK) e un file .pfx del certificato.
rem Uso: sign.bat cert.pfx [password]
rem Esempio: sign.bat betacloud.pfx miaPassword
setlocal
set CERT=%~1
set PFXPASS=%~2
if "%CERT%"=="" (
  echo Uso: sign.bat cert.pfx [password]
  exit /b 1
)
set SIGNTOOL=
for %%K in ("C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe" "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe") do (
  if exist %%K set SIGNTOOL=%%K
)
if "%SIGNTOOL%"=="" (
  for /f "delims=" %%S in ('where signtool 2^>nul') do set SIGNTOOL=%%S
)
if "%SIGNTOOL%"=="" (
  echo signtool non trovato: installa Windows SDK (https://developer.microsoft.com/windows/downloads/windows-sdk/)
  exit /b 1
)
if "%PFXPASS%"=="" (
  "%SIGNTOOL%" sign /f "%CERT%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "dist\BC-Transporter.exe" "installer\out\BC-Transporter-Setup-1.0.0.exe"
) else (
  "%SIGNTOOL%" sign /f "%CERT%" /p "%PFXPASS%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "dist\BC-Transporter.exe" "installer\out\BC-Transporter-Setup-1.0.0.exe"
)
if errorlevel 1 (
  echo Firma fallita.
  exit /b 1
)
echo Firmati: dist\BC-Transporter.exe + installer\out\BC-Transporter-Setup-1.0.0.exe
