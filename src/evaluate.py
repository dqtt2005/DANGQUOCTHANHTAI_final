"""
Mô-đun tính toán các chỉ số đánh giá khoa học theo đúng mục 4.3 của Đề cương:
- Accuracy, Macro-F1 (zero_division=0)
- Recall từng chữ số 0-9
- Confusion Matrix (dạng số đếm và dạng chuẩn hóa theo hàng)
- Chênh lệch điểm phần trăm Delta_pp và tỉ số R theo từng cặp seed
- Vẽ biểu đồ phổ Mel đối sánh: Thật vs Tái tạo vs Sinh từ prior
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any

from .config import (
    TABLES_DIR, FIGURES_DIR, PROCESSED_DATA_DIR, AudioConfig
)
from .dataset import load_norm_stats, invert_zscore


def compute_classification_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
    """
    Tính Accuracy, Macro-F1 (zero_division=0) và Confusion Matrix bằng NumPy thuần
    theo đúng công thức 7 & 8 trong Đề cương.
    """
    y_true_arr = np.array(y_true, dtype=int)
    y_pred_arr = np.array(y_pred, dtype=int)
    num_classes = 10

    # 1. Accuracy (Phương trình 7)
    acc = float(np.mean(y_true_arr == y_pred_arr))

    # 2. Confusion Matrix dạng số đếm
    cm_count = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true_arr, y_pred_arr):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm_count[t, p] += 1

    # Chuẩn hóa theo hàng (nhãn thật)
    row_sums = cm_count.sum(axis=1, keepdims=True)
    cm_norm = np.divide(cm_count, row_sums, out=np.zeros_like(cm_count, dtype=float), where=row_sums != 0)

    # 3. Macro-F1 (Phương trình 8) và Recall từng lớp (zero_division=0)
    per_class_recall = []
    per_class_f1 = []
    for c in range(num_classes):
        tp = cm_count[c, c]
        fn = cm_count[c, :].sum() - tp
        fp = cm_count[:, c].sum() - tp

        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        f1 = float((2.0 * tp) / (2.0 * tp + fp + fn)) if (2.0 * tp + fp + fn) > 0 else 0.0

        per_class_recall.append(rec)
        per_class_f1.append(f1)

    macro_f1 = float(np.mean(per_class_f1))

    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class_recall": per_class_recall,
        "confusion_matrix_count": cm_count.tolist(),
        "confusion_matrix_norm": cm_norm.tolist()
    }


def summarize_paired_experiments(
    results_trtr: List[Dict[str, Any]],
    results_tstr: List[Dict[str, Any]],
    seeds: List[int]
) -> pd.DataFrame:
    """
    Tổng hợp kết quả so sánh ghép cặp TRTR vs TSTR qua các seed.
    Tính Delta_pp = 100 * (acc_TRTR - acc_TSTR) và R = acc_TSTR / acc_TRTR
    """
    rows = []
    delta_pps = []
    rs = []

    for seed, r_trtr, r_tstr in zip(seeds, results_trtr, results_tstr):
        acc_tr = r_trtr["test_acc"]
        acc_ts = r_tstr["test_acc"]
        f1_tr = r_trtr["macro_f1"]
        f1_ts = r_tstr["macro_f1"]

        delta_pp = 100.0 * (acc_tr - acc_ts)
        r_ratio = (acc_ts / acc_tr) if acc_tr > 0 else 0.0

        delta_pps.append(delta_pp)
        rs.append(r_ratio)

        rows.append({
            "Seed": seed,
            "TRTR Accuracy (%)": f"{acc_tr * 100:.2f}",
            "TSTR Accuracy (%)": f"{acc_ts * 100:.2f}",
            "TRTR Macro-F1": f"{f1_tr:.4f}",
            "TSTR Macro-F1": f"{f1_ts:.4f}",
            "Delta_pp (điểm %)": f"{delta_pp:+.2f}",
            "Tỉ số R (TSTR/TRTR)": f"{r_ratio:.4f}"
        })

    # Dòng trung bình +- độ lệch chuẩn
    mean_tr_acc = np.mean([r["test_acc"] for r in results_trtr]) * 100
    std_tr_acc = np.std([r["test_acc"] for r in results_trtr], ddof=1) if len(seeds) > 1 else 0.0

    mean_ts_acc = np.mean([r["test_acc"] for r in results_tstr]) * 100
    std_ts_acc = np.std([r["test_acc"] for r in results_tstr], ddof=1) if len(seeds) > 1 else 0.0

    mean_tr_f1 = np.mean([r["macro_f1"] for r in results_trtr])
    std_tr_f1 = np.std([r["macro_f1"] for r in results_trtr], ddof=1) if len(seeds) > 1 else 0.0

    mean_ts_f1 = np.mean([r["macro_f1"] for r in results_tstr])
    std_ts_f1 = np.std([r["macro_f1"] for r in results_tstr], ddof=1) if len(seeds) > 1 else 0.0

    mean_delta = np.mean(delta_pps)
    std_delta = np.std(delta_pps, ddof=1) if len(seeds) > 1 else 0.0

    mean_r = np.mean(rs)
    std_r = np.std(rs, ddof=1) if len(seeds) > 1 else 0.0

    rows.append({
        "Seed": "Trung bình ± Std",
        "TRTR Accuracy (%)": f"{mean_tr_acc:.2f} ± {std_tr_acc:.2f}",
        "TSTR Accuracy (%)": f"{mean_ts_acc:.2f} ± {std_ts_acc:.2f}",
        "TRTR Macro-F1": f"{mean_tr_f1:.4f} ± {std_tr_f1:.4f}",
        "TSTR Macro-F1": f"{mean_ts_f1:.4f} ± {std_ts_f1:.4f}",
        "Delta_pp (điểm %)": f"{mean_delta:+.2f} ± {std_delta:.2f}",
        "Tỉ số R (TSTR/TRTR)": f"{mean_r:.4f} ± {std_r:.4f}"
    })

    df = pd.DataFrame(rows)
    table_path = TABLES_DIR / "trtr_vs_tstr_summary.csv"
    df.to_csv(table_path, index=False)
    print(f"\n-> Bảng kết quả chính TRTR vs TSTR đã lưu tại: {table_path}")
    print(df.to_string(index=False))

    return df


def plot_confusion_matrices(
    cm_trtr: np.ndarray,
    cm_tstr: np.ndarray,
    save_path: Path
):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    im0 = axes[0].imshow(cm_trtr, interpolation='nearest', cmap=plt.cm.Blues)
    axes[0].set_title("Ma trận nhầm lẫn chuẩn hóa - TRTR (Test thật)", fontsize=12)
    fig.colorbar(im0, ax=axes[0])
    axes[0].set_xlabel("Nhãn dự đoán")
    axes[0].set_ylabel("Nhãn thực tế")
    axes[0].set_xticks(range(10))
    axes[0].set_yticks(range(10))

    im1 = axes[1].imshow(cm_tstr, interpolation='nearest', cmap=plt.cm.Blues)
    axes[1].set_title("Ma trận nhầm lẫn chuẩn hóa - TSTR (Test thật)", fontsize=12)
    fig.colorbar(im1, ax=axes[1])
    axes[1].set_xlabel("Nhãn dự đoán")
    axes[1].set_ylabel("Nhãn thực tế")
    axes[1].set_xticks(range(10))
    axes[1].set_yticks(range(10))

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"-> Đã lưu biểu đồ ma trận nhầm lẫn tại: {save_path}")


def plot_spectrogram_triplet(
    real_sample: np.ndarray,
    recon_sample: np.ndarray,
    syn_sample: np.ndarray,
    digit: int,
    save_path: Path
):
    """
    Vẽ 3 phổ log-mel: Thật x, Tái tạo x_hat, Sinh từ prior x_syn của cùng nhãn digit.
    """
    mu, sigma = load_norm_stats()
    # Khôi phục về dB để trực quan hóa
    L_real = invert_zscore(real_sample, mu, sigma)
    L_recon = invert_zscore(recon_sample, mu, sigma)
    L_syn = invert_zscore(syn_sample, mu, sigma)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    titles = [f"Phổ Thật (Chữ số {digit})", f"Phổ cVAE Tái tạo (x̂)", f"Phổ cVAE Sinh từ prior z~N(0,I)"]

    for ax, spec, title in zip(axes, [L_real, L_recon, L_syn], titles):
        im = ax.imshow(spec, origin='lower', aspect='auto', cmap='viridis')
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Khung thời gian (0-63)")
        ax.set_ylabel("Dải tần Mel (0-63)")
        fig.colorbar(im, ax=ax, format="%+2.0f dB")

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"-> Đã lưu hình so sánh phổ tại: {save_path}")
