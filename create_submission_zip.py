"""
Tạo file nén .zip đóng gói toàn bộ sản phẩm nộp LMS:
- File Word có bìa (DangQuocThanhTai_Bao_cao_cuoi_ky.docx)
- File PowerPoint (DangQuocThanhTai_Bao_cao_cuoi_ky.pptx)
- Mã nguồn src/ và notebook notebooks/
- Dữ liệu manifest, kết quả xuất ESP32, bảng biểu và checkpoint
Loại trừ thư mục ảo .venv và file tạm.
"""

import sys
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
ZIP_PATH = BASE_DIR / "DangQuocThanhTai_23110149_G1_final.zip"

INCLUDE_DIRS = ["src", "notebooks", "outputs", "checkpoints", "data/manifests"]
INCLUDE_FILES = [
    "DangQuocThanhTai_Bao_cao_cuoi_ky.docx",
    "DangQuocThanhTai_Bao_cao_cuoi_ky.pptx",
    "Bao_cao_tieu_luan_DangQuocThanhTai.md",
    "README.md",
    "requirements.txt",
    "run.py",
    "make_word_report.py",
    "make_presentation.py"
]

print(f"Đang đóng gói file nén nộp LMS: {ZIP_PATH} ...")
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    # 1. Thêm các file lẻ gốc
    for fname in INCLUDE_FILES:
        fpath = BASE_DIR / fname
        if fpath.exists():
            zf.write(fpath, arcname=fname)
            print(f" + {fname}")

    # 2. Thêm các thư mục quan trọng
    for dir_rel in INCLUDE_DIRS:
        dp = BASE_DIR / dir_rel
        if dp.exists():
            for item in dp.rglob("*"):
                if item.is_file():
                    # Bỏ qua __pycache__
                    if "__pycache__" in item.parts:
                        continue
                    arc = item.relative_to(BASE_DIR)
                    zf.write(item, arcname=str(arc))
                    print(f" + {arc}")

print(f"\n-> ĐÃ TẠO THÀNH CÔNG FILE NÉN LMS: {ZIP_PATH} ({ZIP_PATH.stat().st_size / (1024*1024):.2f} MB)")
