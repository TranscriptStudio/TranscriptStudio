@echo off
REM ============================================================
REM Build Windows - Transcript Studio 1.0 (P11)
REM
REM Strategie : Nuitka, mode standalone (pas onefile), MSVC.
REM Sortie : build\TranscriptStudio.dist\TranscriptStudio.exe
REM
REM Prerequis :
REM   - Python STANDARD 3.11 (python.org / uv), PAS une distribution
REM     Anaconda/conda : avec Anaconda, "import ctypes" provoque un
REM     abort fatal (0x40000015) dans le binaire standalone, et
REM     platformdirs l'importe au demarrage.
REM     Exemple d'environnement propre :
REM       uv venv --python 3.11 TranscriptStudio_buildenv
REM       uv pip install --python TranscriptStudio_buildenv/Scripts/python.exe ^
REM         -r requirements.txt nuitka ordered-set zstandard
REM   - Les dependances de requirements.txt + nuitka + ordered-set + zstandard
REM   - Visual Studio avec les C++ Build Tools (MSVC)
REM
REM Utilisation, depuis la racine du depot :
REM   tools\build_windows.bat <chemin\vers\python.exe>
REM   (sans argument : "python" du PATH)
REM ============================================================
setlocal
cd /d "%~dp0.."

set PY=%~1
if "%PY%"=="" set PY=python

"%PY%" -m nuitka ^
  --standalone ^
  --assume-yes-for-downloads ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=icons/icon.ico ^
  --company-name="Transcript Studio" ^
  --product-name="Transcript Studio" ^
  --file-description="Transcript Studio - pretraitement audio et transcription" ^
  --file-version=1.0.0.0 ^
  --product-version=1.0.0.0 ^
  --include-data-dir=icons=icons ^
  --include-data-files="docs/Manuel utilisateur.pdf=docs/Manuel utilisateur.pdf" ^
  --include-data-files="tools/ffmpeg/ffmpeg.exe=tools/ffmpeg/windows/ffmpeg.exe" ^
  --include-package-data=qdarktheme ^
  --output-dir=build ^
  TranscriptStudio.py

if errorlevel 1 (
  echo.
  echo ECHEC du build.
  exit /b 1
)

REM ============================================================
REM P11.1 : plugins multimedia Qt (backend QMediaPlayer)
REM
REM Nuitka n'embarque pas automatiquement le repertoire
REM plugins/multimedia de PySide6 ni les DLL FFmpeg (avcodec,
REM avformat, avutil, swresample, swscale) dont depend le
REM backend ffmpegmediaplugin.dll. Sans eux, QMediaPlayer ne
REM peut lire aucun fichier audio dans le binaire standalone.
REM ============================================================
REM NB : pas de "for /f ... usebackq" ici : les guillemets autour de %PY%
REM dans la commande backquotee sont supprimes par cmd /c, ce qui laisse
REM SITEPKGS vide et fait echouer les copies suivantes.
set "SITEPKGS_FILE=%TEMP%\transcriptstudio_sitepkgs.txt"
"%PY%" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])" > "%SITEPKGS_FILE%"
set /p SITEPKGS=<"%SITEPKGS_FILE%"
del "%SITEPKGS_FILE%" >nul 2>&1
if "%SITEPKGS%"=="" (
  echo ECHEC : impossible de localiser site-packages.
  exit /b 1
)
set "DIST=build\TranscriptStudio.dist"

xcopy "%SITEPKGS%\PySide6\plugins\multimedia" "%DIST%\PySide6\qt-plugins\multimedia\" /e /i /y >nul
if errorlevel 1 (
  echo ECHEC : copie des plugins multimedia Qt.
  exit /b 1
)

copy /y "%SITEPKGS%\PySide6\av*.dll" "%DIST%\" >nul
copy /y "%SITEPKGS%\PySide6\sw*.dll" "%DIST%\" >nul
if errorlevel 1 (
  echo ECHEC : copie des DLL FFmpeg de Qt Multimedia.
  exit /b 1
)

echo.
echo Build OK : build\TranscriptStudio.dist\TranscriptStudio.exe
endlocal
