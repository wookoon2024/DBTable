# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller 빌드 설정.  빌드: pyinstaller --noconfirm 전산바이블.spec
#
# 이 파일 없이 `pyinstaller oracle_guide_app.py` 로 빌드하면 안 된다.
# 아래 두 가지를 하지 않으면 결과물이 망가진다.
#
#   1. excludes
#      개발 PC에 torch, scipy, sklearn 등이 깔려 있으면 PyInstaller 가
#      전부 끌어안는다. torch 만으로도 수 GB 라 76MB 짜리 exe 가 수 GB 로
#      부푼다. 특히 PySide6 / PyQt5 는 PyQt6 와 함께 번들되면 Qt 바인딩이
#      충돌해 실행 자체가 깨진다.
#
#   2. collect_data_files('hwpx')
#      python-hwpx 의 템플릿 데이터가 빠지면 HWPX 내보내기가 동작하지 않는다.
#
import os
import base64
from PyInstaller.utils.hooks import collect_data_files

# 업무망 등 .ico 반입이 차단된 환경 대응: app_icon.ico가 없으면 코드 내장 Base64에서 자동 복원
ico_file = 'app_icon.ico'
if not os.path.exists(ico_file) or os.path.getsize(ico_file) == 0:
    try:
        from oracle_guide_app import APP_ICON_BASE64
        with open(ico_file, 'wb') as f:
            f.write(base64.b64decode(APP_ICON_BASE64.strip()))
        print(f"[OK] Automatically restored {ico_file} from embedded code!")
    except Exception as e:
        print(f"[Warning] Failed to restore {ico_file}: {e}")

datas = []
datas += collect_data_files('hwpx')
if os.path.exists('fonts'):
    datas.append(('fonts', 'fonts'))


a = Analysis(
    ['oracle_guide_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'scipy', 'matplotlib', 'sklearn', 'sympy', 'numba', 'IPython', 'jupyter', 'notebook', 'tensorflow', 'PySide6', 'PyQt5', 'tkinter', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='전산바이블',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
