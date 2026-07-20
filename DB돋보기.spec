# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller 빌드 설정.  빌드: pyinstaller --noconfirm DB돋보기.spec
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
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('hwpx')


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
    name='DB돋보기',
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
