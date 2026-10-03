"""
Tạo manifest, phân chia train/val/test không rò rỉ,
tính toán thống kê z-score trên tập Train thật,
và trích xuất lưu trước tensor [B, 1, 64, 64] để tối ưu tốc độ huấn luyện.
Tuân thủ nghiêm ngặt mục 2.1, 2.2, 2.3 của Đề cương.
"""

import os
import sys
import re
import json

# Đảm bảo in tiếng Việt trên console Windows không bị lỗi mã hóa
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import soundfile as sf

from .config import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, MANIFEST_PATH, NORM_STATS_PATH,
    AudioConfig, DatasetConfig
)
from .dataset import process_raw_audio_to_logmel, apply_zscore


def build_manifest(raw_dir: Path, manifest_path: Path) -> pd.DataFrame:
    """
    Quét thư mục recordings, tạo manifest.csv và gán split.
    """
    recordings_dir = raw_dir / "recordings"
    if not recordings_dir.exists():
        # Thử tìm trực tiếp trong raw_dir nếu không có subfolder recordings
        recordings_dir = raw_dir

    wav_files = list(recordings_dir.glob("*.wav"))
    if len(wav_files) == 0:
        raise FileNotFoundError(f"Không tìm thấy file WAV nào trong {recordings_dir}")

    records = []
    # Quy tắc đặt tên FSDD: {digit}_{speaker}_{index}.wav
    pattern = re.compile(r"^(\d+)_([a-zA-Z]+)_(\d+)\.wav$")

    for fpath in wav_files:
        match = pattern.match(fpath.name)
        if not match:
            continue
        digit = int(match.group(1))
        speaker = match.group(2)
        idx = int(match.group(3))

        # Phân chia dữ liệu theo mục 2.2:
        # 0-4: test (300 mẫu)
        # 5-9: val (300 mẫu)
        # 10-49: train (2400 mẫu)
        if 0 <= idx <= 4:
            split = "test"
        elif 5 <= idx <= 9:
            split = "val"
        elif 10 <= idx <= 49:
            split = "train"
        else:
            split = "ignored"

        # Đọc số lượng mẫu tín hiệu gốc
        info = sf.info(str(fpath))
        num_samples = info.frames

        records.append({
            "file_id": fpath.stem,
            "file_name": fpath.name,
            "file_path": str(fpath.resolve()),
            "digit": digit,
            "speaker": speaker,
            "index": idx,
            "num_samples": num_samples,
            "split": split
        })

    df = pd.DataFrame(records)
    # Sắp xếp theo digit, speaker, index để dữ liệu có thứ tự xác định
    df = df.sort_values(by=["digit", "speaker", "index"]).reset_index(drop=True)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(manifest_path, index=False)
    print(f"-> Đã tạo manifest với {len(df)} file tại: {manifest_path}")

    # Báo cáo số lượng từng tập
    for s in ["train", "val", "test"]:
        sub = df[df["split"] == s]
        print(f"   Tập {s.upper()}: {len(sub)} mẫu (Mỗi chữ số: {len(sub)//10} mẫu)")

    # Kiểm tra giao thoa giữa các tập
    train_ids = set(df[df["split"] == "train"]["file_id"])
    val_ids = set(df[df["split"] == "val"]["file_id"])
    test_ids = set(df[df["split"] == "test"]["file_id"])
    assert len(train_ids.intersection(val_ids)) == 0, "LỖI RÒ RỈ: Trùng lặp giữa Train và Val!"
    assert len(train_ids.intersection(test_ids)) == 0, "LỖI RÒ RỈ: Trùng lặp giữa Train và Test!"
    assert len(val_ids.intersection(test_ids)) == 0, "LỖI RÒ RỈ: Trùng lặp giữa Val và Test!"
    print("-> Xác nhận kiểm tra: Không có bất kỳ tệp nào bị giao thoa giữa 3 tập dữ liệu.")

    return df


def prepare_and_cache_dataset():
    audio_cfg = AudioConfig()
    df = build_manifest(RAW_DATA_DIR, MANIFEST_PATH)

    # 1. Tính toán mu, sigma CHỈ TRÊN TẬP TRAIN (2400 mẫu)
    train_df = df[df["split"] == "train"].copy()
    print("\n--- Bước 1: Tính toán thống kê chuẩn hóa trên tập Train ---")
    train_logmels = []
    trimmed_count = 0
    for _, row in tqdm(train_df.iterrows(), total=len(train_df), desc="Extracting Train Log-Mel"):
        L, trimmed = process_raw_audio_to_logmel(row["file_path"], audio_cfg)
        if trimmed:
            trimmed_count += 1
        train_logmels.append(L)

    # Nối theo chiều thời gian (64, 2400 * 64) để tính mu và sigma cho từng dải mel
    concatenated = np.concatenate(train_logmels, axis=1)
    mu = np.mean(concatenated, axis=1)
    sigma = np.std(concatenated, axis=1)

    norm_stats = {
        "mu": mu.tolist(),
        "sigma": sigma.tolist(),
        "trimmed_count": trimmed_count,
        "total_train_samples": len(train_df),
        "target_samples": audio_cfg.target_samples,
        "n_mels": audio_cfg.n_mels
    }
    with open(NORM_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(norm_stats, f, indent=2)
    print(f"-> Thống kê z-score đã lưu tại {NORM_STATS_PATH}")
    print(f"   Số file train bị cắt (dài hơn 8000 mẫu): {trimmed_count}/{len(train_df)} ({trimmed_count/len(train_df)*100:.2f}%)")

    # 2. Xử lý và lưu tensor đã z-score cho từng tập
    print("\n--- Bước 2: Chuẩn hóa z-score và lưu trữ tensor cho Train, Val, Test ---")
    for split_name in ["train", "val", "test"]:
        sub_df = df[df["split"] == split_name].copy().reset_index(drop=True)
        features_list = []
        labels_list = []
        file_ids_list = []

        for _, row in tqdm(sub_df.iterrows(), total=len(sub_df), desc=f"Processing {split_name.upper()}"):
            L, _ = process_raw_audio_to_logmel(row["file_path"], audio_cfg)
            x = apply_zscore(L, mu, sigma, eps=audio_cfg.eps_std)  # [1, 64, 64]
            features_list.append(x)
            labels_list.append(row["digit"])
            file_ids_list.append(row["file_id"])

        features_tensor = torch.from_numpy(np.stack(features_list, axis=0)).float()  # [N, 1, 64, 64]
        labels_tensor = torch.tensor(labels_list, dtype=torch.long)                 # [N]

        # Kiểm tra tự động tính hợp lệ
        assert not torch.isnan(features_tensor).any(), f"Phát hiện NaN trong {split_name}!"
        assert not torch.isinf(features_tensor).any(), f"Phát hiện Inf trong {split_name}!"
        assert features_tensor.shape[1:] == (1, 64, 64), f"Sai kích thước tensor {split_name}: {features_tensor.shape}"

        # Lưu file
        feat_path = PROCESSED_DATA_DIR / f"{split_name}_features.pt"
        lbl_path = PROCESSED_DATA_DIR / f"{split_name}_labels.pt"
        ids_path = PROCESSED_DATA_DIR / f"{split_name}_file_ids.json"

        torch.save(features_tensor, feat_path)
        torch.save(labels_tensor, lbl_path)
        with open(ids_path, "w", encoding="utf-8") as f:
            json.dump(file_ids_list, f, indent=2)

        print(f"   -> Đã lưu {split_name.upper()}: Shape {features_tensor.shape}, Labels {labels_tensor.shape}")

    print("\n=== Hoàn thành chuẩn bị toàn bộ dữ liệu FSDD ===")


if __name__ == "__main__":
    prepare_and_cache_dataset()
