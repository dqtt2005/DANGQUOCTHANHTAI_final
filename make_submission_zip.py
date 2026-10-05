"""
Script đóng gói file nén nộp bài: DangQuocThanhTai_23110149_G1_final.zip
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
import zipfile
import os

BASE_DIR = Path(__file__).resolve().parent
zip_name = "DangQuocThanhTai_23110149_G1_final.zip"
zip_path = BASE_DIR / zip_name

include_patterns = [
    # Báo cáo và trình bày
    "DangQuocThanhTai_Bao_cao_cuoi_ky.docx",
    "DangQuocThanhTai_Bao_cao_cuoi_ky.pptx",
    "Bao_cao_tieu_luan_DangQuocThanhTai.md",
    "README.md",
    "requirements.txt",
    ".gitignore",
    
    # Source code
    "src/",
    "run.py",
    "complete_pipeline.py",
    "make_beautiful_thesis_docx.py",
    "make_exact_15page_docx.py",
    "generate_spectrogram_fig.py",
    "notebooks/",
    
    # Kết quả
    "outputs/figures/",
    "outputs/tables/",
    "outputs/predictions/",
    "outputs/esp32_export/",
    "outputs/cvae_beta1.0_dz32_seed42_history.json",
    "outputs/cvae_beta1.0_dz32_seed7_history.json",
    "outputs/cvae_beta1.0_dz32_seed2026_history.json",
    
    # Data manifests (nhỏ)
    "data/manifests/",
]

exclude_patterns = [
    "__pycache__",
    ".pyc",
    ".venv",
    "checkpoints/",
    "data/raw/",
    "data/processed/",
    "audio_reconstructed/",
    ".git/",
    ".zip",
]

print("=" * 60)
print(f"ĐÓNG GÓI TỆP NỘP BÀI: {zip_name}")
print("=" * 60)

with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
    for pattern in include_patterns:
        target = BASE_DIR / pattern
        if target.is_file():
            arcname = pattern
            zf.write(str(target), arcname)
            print(f"  + {arcname}")
        elif target.is_dir():
            for root, dirs, files in os.walk(str(target)):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(BASE_DIR)
                    rel_str = str(rel_p).replace('\\', '/')
                    
                    # Kiểm tra loại trừ
                    if any(ex in rel_str for ex in exclude_patterns):
                        continue
                    
                    zf.write(str(full_p), rel_str)
                    print(f"  + {rel_str}")

zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
print(f"\n-> Đã tạo thành công file nén: {zip_path}")
print(f"   Kích thước: {zip_size_mb:.2f} MB")
