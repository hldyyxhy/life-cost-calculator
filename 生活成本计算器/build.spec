# -*- coding: utf-8 -*-
"""PyInstaller 打包配置 —— 生活成本计算器

用法：
    pyinstaller build.spec --clean

或等价命令行（无需本文件，效果相同）：
    pyinstaller --onefile --windowed --name "生活成本计算器" --clean main.py

产物：dist/生活成本计算器.exe（单文件，双击即用，无需安装 Python）

要点：
    - 本程序零第三方依赖（仅 tkinter 标准库），且无任何外部资源文件
      （图片 / 字体 / json 模板），因此 datas=[]、hiddenimports=[]。
    - pages 子包经 main.py → gui_app 的 import 链被 PyInstaller 自动收集。
    - --onefile：单个 exe（启动稍慢，因要解压到临时目录；对分发友好，双击即用）。
    - console=False：GUI 程序不弹黑色控制台窗口（即 --windowed）。
    - 用户档案 / 债务状态存在 exe 同级的 data/ 目录，运行时自动创建，
      不打进 exe（详见 profile.app_data_dir）。

更新数据后重新打包：直接重跑上面的 pyinstaller 命令即可，dist/ 会覆盖。
"""
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],                 # 无外部资源（图片/字体/json 模板）需打包
    hiddenimports=[],         # pages 子包由 import 链自动收集
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],              # 不排除标准库，保证运行稳定（体积换可靠）
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
    name='生活成本计算器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                 # 用 UPX 压缩减体积（系统未装 UPX 时自动跳过）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # GUI：不弹控制台黑框（--windowed）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                # 暂无图标；备好 app.ico 后改 icon='app.ico'
    version='version_info.txt',  # Windows 文件版本信息（右键属性→详细信息）；改版本号编辑 version_info.txt
)
