# PyInstaller spec: one-file, windowed (no console) build.
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "eyecare" / "__main__.py")],
    pathex=[str(root)],
    datas=[(str(root / "eyecare" / "assets"), "assets")],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick", "tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="EyeCare",
    console=False,
    icon=str(root / "eyecare" / "assets" / "eyecare.ico"),
    upx=False,
)
