"""
Cấu hình tập trung cho toàn bộ đề tài:
"Sinh đặc trưng log-mel của chữ số nói bằng cVAE và đánh giá theo giao thức TSTR"
Đề cương: Đặng Quốc Thành Tài - MSSV: 23110149 - G1
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple

# Thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent

# Đường dẫn dữ liệu
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw" / "fsdd"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MANIFEST_DIR = DATA_DIR / "manifests"
MANIFEST_PATH = MANIFEST_DIR / "manifest.csv"
NORM_STATS_PATH = MANIFEST_DIR / "norm_stats.json"

# Đường dẫn lưu trữ kết quả và checkpoint
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
OUTPUT_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"
PREDICTIONS_DIR = OUTPUT_DIR / "predictions"
EXPORT_DIR = OUTPUT_DIR / "esp32_export"

# Đảm bảo các thư mục tồn tại
for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MANIFEST_DIR,
          CHECKPOINT_DIR, OUTPUT_DIR, FIGURES_DIR, TABLES_DIR, PREDICTIONS_DIR, EXPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class AudioConfig:
    sample_rate: int = 8000
    target_samples: int = 8000       # 1 giây tín hiệu
    n_fft: int = 256
    win_length: int = 256
    hop_length: int = 128
    window: str = "hann"
    center: bool = True
    pad_mode: str = "constant"
    n_mels: int = 64
    fmin: float = 0.0
    fmax: float = 4000.0
    power: float = 2.0
    htk: bool = False
    norm: str = "slaney"
    ref_value: float = 1.0
    amin: float = 1e-8
    pad_column_db: float = -80.0     # Thêm 1 cột -80 dB để tạo ma trận 64x64
    eps_std: float = 1e-6            # Tránh chia cho 0 khi z-score


@dataclass
class DatasetConfig:
    total_samples: int = 3000
    num_classes: int = 10
    speakers: List[str] = field(default_factory=lambda: [
        "jackson", "nicolas", "theo", "yweweler", "george", "lucas"
    ])
    # Phân chia dữ liệu theo chỉ số bản ghi (0-49)
    test_indices: Tuple[int, int] = (0, 4)     # 300 mẫu (30 mẫu/chữ số)
    val_indices: Tuple[int, int] = (5, 9)      # 300 mẫu (30 mẫu/chữ số)
    train_indices: Tuple[int, int] = (10, 49)  # 2400 mẫu (240 mẫu/chữ số)


@dataclass
class CVAEConfig:
    in_channels: int = 1
    input_height: int = 64
    input_width: int = 64
    num_classes: int = 10
    latent_dim: int = 32             # d_z = 32 mặc định
    beta: float = 1.0                # Trọng số KL mặc định
    learning_rate: float = 1e-3
    weight_decay: float = 0.0
    batch_size: int = 64
    drop_last: bool = False
    max_epochs: int = 100
    patience: int = 10


@dataclass
class ClassifierConfig:
    in_channels: int = 1
    num_classes: int = 10
    dropout_rate: float = 0.2
    learning_rate: float = 1e-3
    weight_decay: float = 0.0
    batch_size: int = 64
    drop_last: bool = False
    max_epochs: int = 50
    patience: int = 10


@dataclass
class ExperimentConfig:
    seeds: List[int] = field(default_factory=lambda: [7, 42, 2026])
    beta_ablation_list: List[float] = field(default_factory=lambda: [0.0, 0.1, 1.0])
    latent_dim_ablation_list: List[int] = field(default_factory=lambda: [16, 32, 64])
    num_synthetic_samples: int = 2400  # 240 mẫu mỗi chữ số (cân bằng 10 lớp)
    primary_ablation_seed: int = 42
