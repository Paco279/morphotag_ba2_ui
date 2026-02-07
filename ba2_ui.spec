# ba2kit-ui.spec
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs, collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

hiddenimports = []
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("faster_whisper")
hiddenimports += collect_submodules("ctranslate2")

binaries = []
binaries += collect_dynamic_libs("ctranslate2")  # DLLs del backend

datas = []
# tu app streamlit
datas += [("app.py", ".")]
# recursos de streamlit (plantillas, etc.)
datas += collect_data_files("streamlit")
# incluye modelo (si lo has puesto)
datas += [("models/small", "models/small")]
# incluye ffmpeg (carpeta con ffmpeg.exe dentro)
datas += [("ffmpeg", "ffmpeg")]

a = Analysis(
    ["app_entry.py"],
    pathex=[],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas,
          name="ba2kit-ui",
          console=False)  # sin consola negra
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="ba2kit-ui")
