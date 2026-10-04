"""
Runner script: Kích hoạt .venv site-packages và thực thi pipeline một cách an toàn.
"""

import sys
from pathlib import Path

# Đảm bảo UTF-8 cho console Windows và flush log ngay lập tức
try:
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
except Exception:
    pass

# Thêm venv site-packages và workspace vào sys.path
BASE_DIR = Path(__file__).resolve().parent
VENV_PACKAGES = BASE_DIR / ".venv" / "Lib" / "site-packages"

import site
site.addsitedir(str(VENV_PACKAGES))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    import src.run_pipeline
    src.run_pipeline.main()
