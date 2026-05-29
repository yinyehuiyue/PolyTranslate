# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('theme.py', '.')]
binaries = []
hiddenimports = ['tkinterdnd2', 'customtkinter', 'openai', 'engine', 'engine.config_manager', 'engine.api_client', 'engine.prompt_builder', 'engine.glossary_manager', 'engine.backup_manager', 'engine.progress_tracker', 'engine.extractor', 'engine.extractor.detector', 'engine.extractor.rpgmaker', 'engine.extractor.renpy', 'engine.extractor.generic', 'engine.injector', 'engine.injector.base_injector', 'engine.injector.file_injector', 'engine.injector.memory_injector', 'memory', 'memory.winapi', 'memory.memory_scanner', 'memory.process_guard', 'memory.shellcode_templates', 'ui', 'ui.main_window', 'ui.settings_dialog', 'ui.style_panel', 'ui.glossary_editor', 'ui.correction_editor', 'ui.widgets', 'utils', 'utils.retry', 'utils.text_guard', 'utils.security', 'utils.error_logger']
tmp_ret = collect_all('openai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'scipy', 'pandas', 'numpy', 'PIL', 'matplotlib'],
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
    name='AI_Translation_Tool_v2',
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
)
