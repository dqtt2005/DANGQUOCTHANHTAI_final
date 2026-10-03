"""
Đo lường chi phí tính toán theo đúng mục 4.5 của Đề cương:
- Đo riêng cVAE, Decoder và Classifier:
  + Số lượng tham số (Parameters)
  + Kích thước file trọng số (.pt)
  + Thời gian suy luận: batch = 1, warm-up 50 lần, đo 200 lần, tính Median và P95
- Tách thời gian trích xuất đặc trưng log-mel khỏi thời gian suy luận mạng
- Báo cáo rõ cấu hình phần cứng máy tính và không kết luận suy diễn về nhúng
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import time
import os
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple

from .config import (
    CHECKPOINT_DIR, TABLES_DIR, AudioConfig
)
from .models.cvae import CVAE, Decoder
from .models.classifier import AudioClassifier
from .dataset import process_raw_audio_to_logmel, apply_zscore, load_norm_stats


def count_parameters(model: torch.nn.Module) -> Tuple[int, int]:
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total_params, trainable_params


def benchmark_latency(
    model: torch.nn.Module,
    dummy_input: Any,
    num_warmup: int = 50,
    num_runs: int = 200,
    device: str = "cpu"
) -> Tuple[float, float]:
    device = torch.device(device)
    model.to(device)
    model.eval()

    # Xử lý input (có thể là tensor hoặc tuple các tensor)
    if isinstance(dummy_input, (list, tuple)):
        inputs = [inp.to(device) for inp in dummy_input]
        forward_fn = lambda: model(*inputs)
    else:
        inp = dummy_input.to(device)
        forward_fn = lambda: model(inp)

    # Warm-up
    with torch.no_grad():
        for _ in range(num_warmup):
            _ = forward_fn()

    # Đo thời gian
    latencies_ms = []
    with torch.no_grad():
        for _ in range(num_runs):
            t0 = time.perf_counter()
            _ = forward_fn()
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    median_lat = float(np.median(latencies_ms))
    p95_lat = float(np.percentile(latencies_ms, 95))
    return median_lat, p95_lat


def benchmark_feature_extraction(
    sample_wav_path: str,
    num_runs: int = 100
) -> Tuple[float, float]:
    """
    Đo thời gian trích xuất đặc trưng log-mel (tách biệt khỏi suy luận mô hình).
    """
    cfg = AudioConfig()
    mu, sigma = load_norm_stats()

    # Warm-up
    for _ in range(10):
        L, _ = process_raw_audio_to_logmel(sample_wav_path, cfg)
        _ = apply_zscore(L, mu, sigma)

    latencies_ms = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        L, _ = process_raw_audio_to_logmel(sample_wav_path, cfg)
        _ = apply_zscore(L, mu, sigma)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    return float(np.median(latencies_ms)), float(np.percentile(latencies_ms, 95))


def run_all_benchmarks(
    sample_wav_path: str,
    device: str = "cpu"
) -> pd.DataFrame:
    print(f"\n=======================================================")
    print(f"BẮT ĐẦU ĐO LƯỜNG CHI PHÍ TÍNH TOÁN (BENCHMARK)")
    print(f"Thiết bị đo: {device.upper()} (batch=1, warm-up=50, runs=200)")
    print(f"=======================================================\n")

    # 1. Trắc nghiệm Feature Extraction
    mel_med, mel_p95 = benchmark_feature_extraction(sample_wav_path)
    print(f"-> Thời gian trích xuất Log-Mel: Trung vị = {mel_med:.2f} ms, P95 = {mel_p95:.2f} ms")

    # 2. Classifier
    clf = AudioClassifier(in_channels=1, num_classes=10)
    clf_ckpt_path = CHECKPOINT_DIR / "classifier_trtr_seed42.pt"
    if clf_ckpt_path.exists():
        ckpt = torch.load(clf_ckpt_path, map_location="cpu")
        clf.load_state_dict(ckpt["model_state_dict"])
        clf_size_kb = os.path.getsize(clf_ckpt_path) / 1024.0
    else:
        clf_size_kb = 0.0

    clf_params, _ = count_parameters(clf)
    dummy_x = torch.randn(1, 1, 64, 64)
    clf_med, clf_p95 = benchmark_latency(clf, dummy_x, device=device)

    # 3. cVAE
    cvae = CVAE(in_channels=1, latent_dim=32, num_classes=10)
    cvae_ckpt_path = CHECKPOINT_DIR / "cvae_beta1.0_dz32_seed42.pt"
    if cvae_ckpt_path.exists():
        ckpt = torch.load(cvae_ckpt_path, map_location="cpu")
        cvae.load_state_dict(ckpt["model_state_dict"])
        cvae_size_kb = os.path.getsize(cvae_ckpt_path) / 1024.0
    else:
        cvae_size_kb = 0.0

    cvae_params, _ = count_parameters(cvae)
    dummy_c = torch.tensor([0])
    cvae_med, cvae_p95 = benchmark_latency(cvae, (dummy_x, dummy_c), device=device)

    # 4. Decoder (Phục vụ sinh mẫu)
    decoder = cvae.decoder
    dec_params, _ = count_parameters(decoder)
    dummy_z = torch.randn(1, 32)
    dummy_onehot = torch.zeros(1, 10)
    dummy_onehot[0, 0] = 1.0
    dec_med, dec_p95 = benchmark_latency(decoder, (dummy_z, dummy_onehot), device=device)

    rows = [
        {
            "Thành phần": "Trích xuất Log-Mel (CPU)",
            "Số tham số": "N/A",
            "Kích thước file (.pt)": "N/A",
            "Độ trễ Trung vị (ms)": f"{mel_med:.2f}",
            "Độ trễ P95 (ms)": f"{mel_p95:.2f}"
        },
        {
            "Thành phần": "Classifier (CNN)",
            "Số tham số": f"{clf_params:,}",
            "Kích thước file (.pt)": f"{clf_size_kb:.1f} KB" if clf_size_kb > 0 else "N/A",
            "Độ trễ Trung vị (ms)": f"{clf_med:.2f}",
            "Độ trễ P95 (ms)": f"{clf_p95:.2f}"
        },
        {
            "Thành phần": "Decoder (Sinh mẫu cVAE)",
            "Số tham số": f"{dec_params:,}",
            "Kích thước file (.pt)": "Nằm trong cVAE",
            "Độ trễ Trung vị (ms)": f"{dec_med:.2f}",
            "Độ trễ P95 (ms)": f"{dec_p95:.2f}"
        },
        {
            "Thành phần": "cVAE Đầy đủ (Encoder + Decoder)",
            "Số tham số": f"{cvae_params:,}",
            "Kích thước file (.pt)": f"{cvae_size_kb:.1f} KB" if cvae_size_kb > 0 else "N/A",
            "Độ trễ Trung vị (ms)": f"{cvae_med:.2f}",
            "Độ trễ P95 (ms)": f"{cvae_p95:.2f}"
        }
    ]

    df = pd.DataFrame(rows)
    save_path = TABLES_DIR / "computational_cost_benchmark.csv"
    df.to_csv(save_path, index=False)
    print(f"\n-> Bảng chi phí tính toán đã lưu tại: {save_path}")
    print(df.to_string(index=False))

    return df
