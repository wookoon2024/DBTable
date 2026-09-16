@echo off
rem =====================================================================
rem  전산 바이블 EXE 빌드 스크립트
rem  - dist 폴더를 삭제하지 않고 전산바이블.exe 만 덮어써서 빌드합니다.
rem =====================================================================
cd /d "%~dp0"
pyinstaller --noconfirm 전산바이블.spec
copy /y dist\전산바이블.exe dist\DB돋보기.exe >nul
copy /y metadata.db dist\metadata.db >nul
if exist attachments xcopy /e /i /y attachments dist\attachments >nul
echo.
echo ===================================================
echo  빌드 완료: dist\전산바이블.exe (DB 및 첨부파일 동기화 완료)
echo ===================================================
pause
