# ba2kit-ui-qt.spec
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs, collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

hiddenimports = []
hiddenimports += collect_submodules("PySide6")
hiddenimports += collect_submodules("shiboken6")
hiddenimports += collect_submodules("faster_whisper")
hiddenimports += collect_submodules("ctranslate2")

binaries = []
binaries += collect_dynamic_libs("ctranslate2")

datas = []
datas += collect_data_files("PySide6")  # recursos Qt
datas += [("models/small", "models/small")]   # modelo offline (si existe)
datas += [("ffmpeg", "ffmpeg")]               # ffmpeg\ffmpeg.exe

a = Analysis(
    ["app_qt.py"],
    pathex=[],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas,
          name="ba2kit-ui",
          console=False)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="ba2kit-ui")
