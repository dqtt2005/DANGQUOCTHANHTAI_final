"""
Script cập nhật file Word và tạo file nén nộp bài.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
import zipfile
import os

BASE_DIR = Path(__file__).resolve().parent
GITHUB_URL = "https://github.com/dqtt2005/DANGQUOCTHANHTAI_final"

# =====================================================
# PHẦN 1: CẬP NHẬT WORD - THÊM LINK GITHUB
# =====================================================
print("=" * 60)
print("CẬP NHẬT FILE WORD VỚI ĐƯỜNG LINK GITHUB")
print("=" * 60)

doc = Document(str(BASE_DIR / "DangQuocThanhTai_Bao_cao_cuoi_ky.docx"))

# Tìm paragraph "TÓM TẮT BÁO CÁO" và thêm thông tin GitHub sau đó
found_summary = False
insert_idx = None
for i, p in enumerate(doc.paragraphs):
    if 'TÓM TẮT BÁO CÁO' in p.text:
        found_summary = True
        insert_idx = i + 1
        break

if found_summary and insert_idx is not None:
    # Thêm đoạn thông tin nộp bài ngay sau tóm tắt
    # Tìm paragraph hiện tại sau tóm tắt
    existing_para = doc.paragraphs[insert_idx]
    
    # Thêm thông tin GitHub vào cuối paragraph tóm tắt
    summary_para = doc.paragraphs[insert_idx]
    
    # Tạo paragraph mới chèn vào trước chương 1
    # Tìm vị trí Chương 1
    ch1_idx = None
    for i, p in enumerate(doc.paragraphs):
        if 'CHƯƠNG 1' in p.text:
            ch1_idx = i
            break
    
    if ch1_idx:
        # Thêm paragraph thông tin nộp bài trước Chương 1
        p_new = doc.paragraphs[ch1_idx - 1]  # paragraph trước Chương 1
        
        # Thêm paragraph mới sau tóm tắt
        from docx.oxml import OxmlElement
        new_p = OxmlElement('w:p')
        p_new._element.addnext(new_p)
        
        # Tạo run cho text
        from lxml import etree
        nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        # Paragraph properties
        pPr = OxmlElement('w:pPr')
        spacing = OxmlElement('w:spacing')
        spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}before', '120')
        spacing.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}after', '120')
        pPr.append(spacing)
        new_p.insert(0, pPr)
        
        # Bold label
        run_label = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        b = OxmlElement('w:b')
        rPr.append(b)
        sz = OxmlElement('w:sz')
        sz.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '22')
        rPr.append(sz)
        run_label.append(rPr)
        t = OxmlElement('w:t')
        t.text = "Mã nguồn GitHub: "
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        run_label.append(t)
        new_p.append(run_label)
        
        # Link text
        run_link = OxmlElement('w:r')
        rPr2 = OxmlElement('w:rPr')
        color = OxmlElement('w:color')
        color.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '0563C1')
        rPr2.append(color)
        u = OxmlElement('w:u')
        u.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'single')
        rPr2.append(u)
        sz2 = OxmlElement('w:sz')
        sz2.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '22')
        rPr2.append(sz2)
        run_link.append(rPr2)
        t2 = OxmlElement('w:t')
        t2.text = GITHUB_URL
        run_link.append(t2)
        new_p.append(run_link)

print("-> Da them link GitHub vao file Word.")

# Lưu file Word đã cập nhật
output_docx = BASE_DIR / "DangQuocThanhTai_Bao_cao_cuoi_ky.docx"
doc.save(str(output_docx))
print(f"-> Da luu file Word: {output_docx}")

# =====================================================
# PHẦN 2: TẠO FILE NÉN NỘP BÀI
# =====================================================
print("\n" + "=" * 60)
print("TẠO FILE NÉN NỘP BÀI")
print("=" * 60)

zip_name = "DangQuocThanhTai_23110149_G1_final.zip"
zip_path = BASE_DIR / zip_name

# Danh sách file/thư mục cần đưa vào file nén
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

# Loại trừ
exclude_patterns = [
    "__pycache__",
    ".pyc",
    ".venv",
    "checkpoints/",
    "data/raw/",
    "data/processed/",
    ".git/",
]

def should_exclude(filepath):
    for pat in exclude_patterns:
        if pat in filepath:
            return True
    return False

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for pattern in include_patterns:
        full_path = BASE_DIR / pattern
        if full_path.is_file():
            arcname = pattern
            if not should_exclude(arcname):
                zf.write(full_path, arcname)
                print(f"  + {arcname}")
        elif full_path.is_dir():
            for root, dirs, files in os.walk(full_path):
                # Loại trừ thư mục
                dirs[:] = [d for d in dirs if not should_exclude(d)]
                for fname in files:
                    fpath = Path(root) / fname
                    arcname = str(fpath.relative_to(BASE_DIR))
                    if not should_exclude(arcname):
                        zf.write(fpath, arcname)
                        print(f"  + {arcname}")

zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"\n-> Da tao file nen: {zip_path}")
print(f"   Kich thuoc: {zip_size_mb:.2f} MB")

# =====================================================
# TỔNG KẾT
# =====================================================
print("\n" + "=" * 60)
print("DANH SÁCH FILE NỘP BÀI")
print("=" * 60)
print(f"""
1. FILE WORD (có bìa):
   -> {output_docx.name}

2. FILE TRÌNH BÀY POWERPOINT:
   -> DangQuocThanhTai_Bao_cao_cuoi_ky.pptx (12 slides)

3. ĐƯỜNG LINK GITHUB (đã ghi trong file Word):
   -> {GITHUB_URL}
   
   *** LƯU Ý: Bạn cần tạo repo GitHub và push code lên ***
   Bước 1: Vào https://github.com/new -> Tạo repo "cVAE-LogMel-TSTR-G1"
   Bước 2: Chạy lệnh sau trong terminal:
   
     git remote add origin {GITHUB_URL}.git
     git branch -M main
     git push -u origin main
   
   Nếu tên GitHub của bạn khác "DangQuocThanhTai", hãy đổi URL tương ứng.

4. FILE NÉN ĐÍNH KÈM LMS:
   -> {zip_name} ({zip_size_mb:.2f} MB)
""")
