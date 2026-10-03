# Sinh Đặc Trưng Log-Mel Của Chữ Số Nói Bằng cVAE và Đánh Giá Theo Giao Thức TSTR

**Đề tài thực nghiệm:** Trí tuệ nhân tạo cho IoT (261AIOT331185_01CLC)  
**Mã đề tài:** G1  
**Sinh viên:** Đặng Quốc Thành Tài  
**MSSV:** 23110149  
**Giảng viên hướng dẫn:** Hồ Nhựt Minh  
**Bộ dữ liệu:** Free Spoken Digit Dataset (FSDD)  

---

## 1. Giới thiệu Đề tài

Đề tài khảo sát tính hữu ích của dữ liệu tổng hợp (synthetic data) được sinh bởi mô hình **cVAE (Conditional Variational Autoencoder)** đối với bài toán nhận dạng chữ số nói trên cơ sở bộ dữ liệu FSDD (3.000 file WAV, 10 chữ số, 6 người nói). 

- **Đầu ra mô hình:** Ma trận đặc trưng phổ log-mel kích thước $1 \times 64 \times 64$.
- **Giao thức đánh giá:** Đối chuẩn **TRTR** (Train on Real, Test on Real) làm mốc tham chiếu và **TSTR** (Train on Synthetic, Test on Real) để đo lường mức độ suy giảm hiệu năng $\Delta_{pp}$ (điểm phần trăm) và tỉ số chuyển giao $R = a_{TSTR} / a_{TRTR}$.
- **Tính khoa học & Liêm chính:** Phân chia dữ liệu train/val/test có manifest cố định, không rò rỉ; thống kê chuẩn hóa $z$-score chỉ lấy từ tập Train thật; khởi tạo cùng trọng số ban đầu cho mỗi seed; công bố minh bạch việc dùng validation thật để chọn checkpoint; đánh giá trên 3 seed độc lập (7, 42, 2026).
- **Sẵn sàng cho IoT / ESP32:** Cung cấp mô-đun xuất mô hình sang ONNX, mảng C header (`model_data.h`) và template C++ nhúng tối ưu cho vi điều khiển ESP32 với ngân sách bộ nhớ thực tế.

---

## 2. Cấu trúc Thư mục Dự án

```text
DangQuocThanhTai_final/
├── data/
│   ├── raw/fsdd/                  # 3.000 file WAV FSDD gốc
│   ├── processed/                 # Tensor PyTorch đã z-score ([N, 1, 64, 64]) và file_ids
│   └── manifests/
│       ├── manifest.csv           # Danh mục 3.000 file gán split train(2400)/val(300)/test(300)
│       └── norm_stats.json        # Thống kê mu, sigma tính trên tập Train thật
├── src/
│   ├── __init__.py
│   ├── config.py                  # Cấu hình siêu tham số (Audio, cVAE, Classifier, Seeds)
│   ├── dataset.py                 # Pipeline đọc WAV, cắt/đệm 8000 mẫu, Mel 64x64, z-score
│   ├── prepare_data.py            # Quét dữ liệu, tạo manifest, trích xuất và cache tensor
│   ├── loss.py                    # Loss conditional ELBO (L_rec, L_KL, L_beta)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── cvae.py                # Encoder 4 tầng Conv, Decoder 4 tầng ConvTranspose
│   │   └── classifier.py          # CNN 3 khối Conv2D-ReLU-MaxPool, Dense(64, 10)
│   ├── train_cvae.py              # Huấn luyện cVAE, early stopping theo val loss
│   ├── generate_synthetic.py      # Lấy mẫu z ~ N(0, I), sinh 2.400 mẫu tổng hợp cân bằng
│   ├── train_classifier.py        # Huấn luyện Classifier TRTR và TSTR (ghép cặp cùng seed)
│   ├── evaluate.py                # Tính Accuracy, Macro-F1, Ma trận nhầm lẫn, Delta_pp, R
│   ├── ablation_beta.py           # Khảo sát độ nhạy beta in {0.0, 0.1, 1.0}
│   ├── benchmark_cost.py          # Đo tham số, kích thước file, latency P50/P95
│   ├── esp32_export.py            # Xuất ONNX, C header array, phân tích bộ nhớ ESP32
│   ├── audio_reconstruct.py       # Khôi phục âm thanh nghe thử bằng Griffin-Lim
│   └── run_pipeline.py            # Script master chạy toàn bộ thí nghiệm tuần tự
├── checkpoints/                   # Trọng số PyTorch (.pt) đã lưu
├── outputs/
│   ├── figures/                   # Biểu đồ ma trận nhầm lẫn, phổ thật vs tái tạo vs sinh
│   ├── tables/                    # File CSV tổng hợp TRTR vs TSTR, ablation, benchmark
│   ├── predictions/               # Dự đoán từng mẫu phục vụ so sánh ghép cặp
│   ├── audio_reconstructed/       # File WAV nghe thử khôi phục từ phổ sinh
│   └── esp32_export/              # File ONNX, model_data.h và code mẫu C++ cho ESP32
├── notebooks/
│   └── 01_reproduce_report.ipynb  # Notebook Jupyter trực quan hóa báo cáo
├── requirements.txt               # Danh sách thư viện phụ thuộc
└── README.md                      # Hướng dẫn chi tiết này
```

---

## 3. Yêu cầu Môi trường & Cài đặt

Dự án được tối ưu để thực thi mượt mà trên môi trường CPU hoặc GPU.

### Yêu cầu hệ thống:
- Hệ điều hành: Windows / Linux / macOS
- Python: Phiên bản 3.10, 3.11 hoặc 3.12 (khuyến nghị Python 3.11)
- Trình quản lý gói: `uv` hoặc `pip`

### Các bước cài đặt:

```bash
# 1. Tạo môi trường ảo
python -m venv .venv

# Kích hoạt trên Windows:
.venv\Scripts\activate
# Kích hoạt trên Linux/macOS:
source .venv/bin/activate

# 2. Cài đặt các thư viện cần thiết
pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu
pip install librosa soundfile scikit-learn matplotlib pandas onnx onnxruntime tqdm
```

Hoặc cài đặt nhanh qua `uv`:
```bash
uv pip install -r requirements.txt
```

---

## 4. Hướng dẫn Tái lập Kết quả Thực nghiệm (Step-by-Step)

### Bước 1: Tiền xử lý dữ liệu và tạo Manifest
Chạy script quét 3.000 file WAV từ `data/raw/fsdd`, tạo `manifest.csv`, tính thống kê $z$-score trên tập Train thật và lưu tensor đã tiền xử lý vào `data/processed/`:
```bash
python -m src.prepare_data
```

### Bước 2: Chạy toàn bộ Thực nghiệm Tự động (Master Pipeline)
Lệnh duy nhất thực thi tuần tự từ huấn luyện TRTR/TSTR qua 3 seed, cVAE, khảo sát $\beta$, đo lường chi phí đến xuất mô hình ESP32:
```bash
python -m src.run_pipeline
```

### Hoặc chạy từng mô-đun độc lập:
- **Huấn luyện cVAE đơn lẻ:**
  ```bash
  python -m src.train_cvae
  ```
- **Sinh mẫu tổng hợp từ prior $z \sim \mathcal{N}(0, I)$:**
  ```bash
  python -m src.generate_synthetic
  ```
- **Khảo sát độ nhạy $\beta \in \{0, 0.1, 1\}$:**
  ```bash
  python -m src.ablation_beta
  ```
- **Đo lường chi phí tính toán:**
  ```bash
  python -m src.benchmark_cost
  ```
- **Đóng gói và xuất mô hình cho ESP32:**
  ```bash
  python -m src.esp32_export
  ```

---

## 5. Quy chuẩn Đánh giá Khoa học & Chỉ số

1. **Phân chia dữ liệu (Data Split):**
   - **Train thật:** Chỉ số `10–49` (2.400 mẫu, 240 mẫu/lớp).
   - **Validation thật:** Chỉ số `5–9` (300 mẫu, 30 mẫu/lớp).
   - **Test thật:** Chỉ số `0–4` (300 mẫu, 30 mẫu/lớp).
2. **So sánh ghép cặp (Paired Comparison):**
   - Đánh giá trên 3 seed: `7`, `42`, `2026`.
   - Với mỗi seed, classifier TRTR và TSTR được khởi tạo cùng một ma trận trọng số ban đầu.
   - Độ chênh lệch điểm phần trăm: $\Delta_{pp} = 100 \times (a_{TRTR} - a_{TSTR})$.
   - Tỉ số năng lực chuyển giao: $R = a_{TSTR} / a_{TRTR}$.
3. **Triển khai Nhúng trên ESP32:**
   - Bộ nhớ Flash: Mô hình Classifier chỉ chiếm ~85 KB (FP32) hoặc ~22 KB (INT8) $\ll$ 4 MB Flash của ESP32.
   - Bộ nhớ RAM: Tensor Arena yêu cầu ~64 KB $\ll$ 320 KB SRAM khả dụng của ESP32.
   - Sẵn sàng tích hợp qua file header `outputs/esp32_export/model_data.h`.

---

## 6. Trích dẫn & Tài liệu Tham khảo

- [1] Kingma, D. P., & Welling, M. (2013). *Auto-Encoding Variational Bayes*. arXiv:1312.6114.
- [2] Sohn, K., Lee, H., & Yan, X. (2015). *Learning Structured Output Representation using Deep Conditional Generative Models*. NeurIPS.
- [3] Esteban, C., Hyland, S. L., & Rätsch, G. (2017). *Real-valued (Medical) Time Series Generation with Recurrent Conditional GANs*. arXiv:1706.02633.
- [4] Free Spoken Digit Dataset (FSDD): `https://github.com/Jakobovski/free-spoken-digit-dataset`.
- [5] Librosa Documentation (v0.11.0): `librosa.feature.melspectrogram`, `librosa.feature.inverse.mel_to_audio`.
