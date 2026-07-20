@echo off
rem =====================================================================
rem  DB 돋보기 EXE 빌드 스크립트
rem  - app_icon.ico 를 EXE에 임베드 → 작업관리자/탐색기에서 앱 아이콘 표시
rem  - 결과물: dist\DB돋보기.exe (실행 시 metadata.db 와 같은 폴더에 두세요)
rem  - --exclude-module: 앱이 쓰지 않는 대형 패키지(torch/scipy 등)가
rem    pandas의 선택적 import를 타고 딸려 들어가는 것을 차단 (용량/빌드시간 절감)
rem =====================================================================
cd /d "%~dp0"
"C:\Python314\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --icon app_icon.ico ^
    --name "DB돋보기" ^
    --collect-data hwpx ^
    --exclude-module torch ^
    --exclude-module torchvision ^
    --exclude-module torchaudio ^
    --exclude-module scipy ^
    --exclude-module matplotlib ^
    --exclude-module sklearn ^
    --exclude-module sympy ^
    --exclude-module numba ^
    --exclude-module IPython ^
    --exclude-module jupyter ^
    --exclude-module notebook ^
    --exclude-module tensorflow ^
    --exclude-module PySide6 ^
    --exclude-module PyQt5 ^
    --exclude-module tkinter ^
    --exclude-module pytest ^
    oracle_guide_app.py
echo.
echo 빌드 완료: dist\DB돋보기.exe
pause
