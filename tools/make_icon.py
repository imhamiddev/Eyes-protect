"""Generate eyecare/assets/eyecare.ico from the brand mark."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from eyecare.ui import brand  # noqa: E402

app = QGuiApplication([])
out = Path(__file__).resolve().parent.parent / "eyecare" / "assets"
big = out / "logo.png"
brand.logo_pixmap(256).save(str(big))

from PIL import Image  # noqa: E402

Image.open(big).save(out / "eyecare.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
print("wrote", out / "eyecare.ico")
