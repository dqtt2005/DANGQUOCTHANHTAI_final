"""
Mô-đun tiền xử lý dữ liệu âm thanh và Dataset cho FSDD theo đúng chuẩn mục 2.3 của Đề cương:
- Đọc 8 kHz mono, [-1, 1]
- Cắt/đệm 8.000 mẫu (thêm 0 ở cuối nếu ngắn, lấy giữa nếu dài)
- STFT n_fft=win_length=256, hop=128, Hann, center=True, pad_mode=constant
- Mel 64 dải, 0-4000 Hz, power=2, slaney
- Log-mel dB: 10 * log10(max(M, 1e-8)), thêm 1 cột -80 dB ở cuối -> 64x64
- Z-score chuẩn hóa theo từng dải mel dựa trên thống kê tập Train thật
"""

import json
import numpy as np
import soundfile as sf
import librosa
import torch
from torch.utils.data import Dataset
from pathlib import Path
from typing import Tuple, Dict, Optional, List
import pandas as pd

from .config import AudioConfig, NORM_STATS_PATH


def process_raw_audio_to_logmel(
    audio_path: str,
    cfg: AudioConfig = AudioConfig()
) -> Tuple[np.ndarray, bool]:
    """
    Tiền xử lý 1 file audio WAV thành ma trận log-mel 64x64 (chưa chuẩn hóa z-score).
    Trả về: (L_matrix [64, 64], was_trimmed: bool)
    """
    # Bước 1: Đọc WAV ở 8 kHz, mono, thang [-1, 1]
    y, sr = sf.read(audio_path, dtype='float32')
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != cfg.sample_rate:
        y = librosa.resample(y, orig_sr=sr, target_sr=cfg.sample_rate)

    # Bước 2: Cố định độ dài 8.000 mẫu
    was_trimmed = False
    orig_len = len(y)
    if orig_len < cfg.target_samples:
        pad_len = cfg.target_samples - orig_len
        y = np.pad(y, (0, pad_len), mode='constant')
    elif orig_len > cfg.target_samples:
        was_trimmed = True
        start = (orig_len - cfg.target_samples) // 2
        y = y[start : start + cfg.target_samples]

    # Bước 3: Tính phổ công suất mel
    # STFT: n_fft=256, win_length=256, hop_length=128, Hann, center=True, pad_mode='constant'
    mel_power = librosa.feature.melspectrogram(
        y=y,
        sr=cfg.sample_rate,
        n_fft=cfg.n_fft,
        win_length=cfg.win_length,
        hop_length=cfg.hop_length,
        window=cfg.window,
        center=cfg.center,
        pad_mode=cfg.pad_mode,
        n_mels=cfg.n_mels,
        fmin=cfg.fmin,
        fmax=cfg.fmax,
        power=cfg.power,
        htk=cfg.htk,
        norm=cfg.norm
    )  # Kích thước: (64, 63)

    # Bước 4: Đổi sang dB: L = 10 * log10(max(M, 1e-8)), mốc tham chiếu 1.0
    L = 10.0 * np.log10(np.maximum(mel_power, cfg.amin))

    # Thêm 1 cột -80 dB ở cuối để có 64 x 64
    pad_col = np.full((cfg.n_mels, 1), cfg.pad_column_db, dtype=np.float32)
    L = np.concatenate([L, pad_col], axis=1)  # Kích thước: (64, 64)

    return L.astype(np.float32), was_trimmed


def compute_train_norm_stats(
    train_df: pd.DataFrame,
    cfg: AudioConfig = AudioConfig()
) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Tính trung bình mu và độ lệch chuẩn sigma theo từng dải mel
    trên TOÀN BỘ khung thời gian của tập TRAIN (đã bổ sung cột).
    """
    print(f"Đang tính toán thống kê chuẩn hóa z-score trên {len(train_df)} mẫu tập Train...")
    all_frames = []
    trimmed_count = 0

    for _, row in train_df.iterrows():
        L, was_trimmed = process_raw_audio_to_logmel(row["file_path"], cfg)
        if was_trimmed:
            trimmed_count += 1
        all_frames.append(L)  # mỗi L có shape (64, 64)

    # Ghép tất cả theo trục thời gian: (64, N_train * 64)
    concatenated = np.concatenate(all_frames, axis=1)
    mu = np.mean(concatenated, axis=1)  # (64,)
    sigma = np.std(concatenated, axis=1)  # (64,)

    stats = {
        "mu": mu.tolist(),
        "sigma": sigma.tolist(),
        "trimmed_count": trimmed_count,
        "total_train_samples": len(train_df)
    }

    NORM_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NORM_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Đã lưu thống kê chuẩn hóa tại: {NORM_STATS_PATH}")
    print(f"Số lượng bản ghi tập Train bị cắt: {trimmed_count}/{len(train_df)}")

    return mu.astype(np.float32), sigma.astype(np.float32), trimmed_count


def load_norm_stats() -> Tuple[np.ndarray, np.ndarray]:
    """
    Tải thống kê mu và sigma từ file norm_stats.json.
    """
    if not NORM_STATS_PATH.exists():
        raise FileNotFoundError(f"Chưa tìm thấy {NORM_STATS_PATH}. Hãy chạy tính toán trên tập Train trước.")
    with open(NORM_STATS_PATH, "r", encoding="utf-8") as f:
        stats = json.load(f)
    mu = np.array(stats["mu"], dtype=np.float32)
    sigma = np.array(stats["sigma"], dtype=np.float32)
    return mu, sigma


def apply_zscore(L: np.ndarray, mu: np.ndarray, sigma: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """
    Chuẩn hóa z-score: x = (L - mu) / max(sigma, eps)
    L: (64, 64)
    mu: (64,)
    sigma: (64,)
    Trả về: x [1, 64, 64]
    """
    x = (L - mu[:, None]) / np.maximum(sigma[:, None], eps)
    return x[None, :, :].astype(np.float32)  # Thêm channel dim -> [1, 64, 64]


def invert_zscore(x: np.ndarray, mu: np.ndarray, sigma: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """
    Khôi phục ngược từ z-score về log-mel dB:
    L = x * max(sigma, eps) + mu
    """
    if x.ndim == 3 and x.shape[0] == 1:
        x = x[0]
    L = x * np.maximum(sigma[:, None], eps) + mu[:, None]
    return L


class FSDDLogMelDataset(Dataset):
    """
    PyTorch Dataset nạp các ma trận log-mel [1, 64, 64] và nhãn tương ứng.
    """
    def __init__(
        self,
        features: torch.Tensor,
        labels: torch.Tensor,
        file_ids: Optional[List[str]] = None
    ):
        self.features = features.float()  # [N, 1, 64, 64]
        self.labels = labels.long()       # [N]
        self.file_ids = file_ids if file_ids is not None else [str(i) for i in range(len(labels))]

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, str]:
        return self.features[idx], self.labels[idx], self.file_ids[idx]
