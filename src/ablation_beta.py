"""
Khảo sát độ nhạy của trọng số beta in {0.0, 0.1, 1.0} theo đúng mục 4.4 của Đề cương:
- beta = 0: Đối chứng bỏ ràng buộc prior (chỉ tối ưu tái tạo, z~N(0,I) có thể không phù hợp)
- beta = 0.1: Regularization yếu
- beta = 1.0: Chuẩn conditional ELBO
Chạy trên seed 42, sinh 2.400 mẫu tổng hợp và đánh giá TSTR tương ứng.
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import torch
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

from .config import (
    CHECKPOINT_DIR, OUTPUT_DIR, TABLES_DIR, PROCESSED_DATA_DIR,
    ExperimentConfig
)
from .train_cvae import train_single_cvae
from .generate_synthetic import generate_synthetic_dataset
from .train_classifier import train_single_classifier
from .models.classifier import AudioClassifier
from .evaluate import compute_classification_metrics


def run_beta_ablation(
    beta_list: List[float] = [0.0, 0.1, 1.0],
    seed: int = 42,
    device: str = "cpu"
) -> pd.DataFrame:
    print(f"\n=======================================================")
    print(f"BẮT ĐẦU KHẢO SÁT ĐỘ NHẠY TRỌNG SỐ BETA: {beta_list}")
    print(f"=======================================================\n")

    val_x = torch.load(PROCESSED_DATA_DIR / "val_features.pt")
    val_y = torch.load(PROCESSED_DATA_DIR / "val_labels.pt")
    test_x = torch.load(PROCESSED_DATA_DIR / "test_features.pt")
    test_y = torch.load(PROCESSED_DATA_DIR / "test_labels.pt")

    # Khởi tạo mô hình classifier cố định cho seed 42
    torch.manual_seed(seed)
    initial_classifier = AudioClassifier(in_channels=1, num_classes=10)

    # Nạp kết quả TRTR seed 42 để làm mốc đối chứng
    trtr_preds_path = OUTPUT_DIR / "predictions" / f"preds_trtr_seed{seed}.csv"
    if trtr_preds_path.exists():
        trtr_df = pd.read_csv(trtr_preds_path)
        trtr_acc = trtr_df["is_correct"].mean()
    else:
        trtr_acc = 0.90  # Giá trị tạm nếu chưa chạy TRTR

    rows = []

    for beta in beta_list:
        print(f"\n---> Khảo sát với beta = {beta} <---")
        existing_ckpt = CHECKPOINT_DIR / f"cvae_beta{beta}_dz32_seed{seed}.pt"
        existing_hist = OUTPUT_DIR / f"cvae_beta{beta}_dz32_seed{seed}_history.json"
        
        if existing_ckpt.exists() and existing_hist.exists():
            print(f"-> Tái sử dụng checkpoint cVAE có sẵn: {existing_ckpt}")
            with open(existing_hist, "r", encoding="utf-8") as f:
                cvae_hist = json.load(f)
            best_val = min(cvae_hist["val_loss"])
            best_ep = cvae_hist["val_loss"].index(best_val) + 1
            cvae_res = {
                "checkpoint_path": str(existing_ckpt),
                "history_path": str(existing_hist),
                "best_epoch": best_ep,
                "best_val_loss": best_val
            }
        else:
            # 1. Huấn luyện cVAE
            cvae_res = train_single_cvae(
                beta=beta,
                latent_dim=32,
                seed=seed,
                max_epochs=100,
                patience=10,
                device=device,
                save_prefix=f"cvae"
            )

        # 2. Sinh tập tổng hợp từ prior z ~ N(0, I)
        ckpt_path = Path(cvae_res["checkpoint_path"])
        syn_features, syn_labels, _ = generate_synthetic_dataset(
            cvae_checkpoint_path=ckpt_path,
            num_samples_per_class=240,
            seed=seed,
            device=device,
            output_prefix=f"synthetic_beta{beta}"
        )

        # 3. Huấn luyện TSTR classifier
        tstr_res = train_single_classifier(
            train_x=syn_features,
            train_y=syn_labels,
            val_x=val_x,
            val_y=val_y,
            test_x=test_x,
            test_y=test_y,
            initial_model=initial_classifier,
            mode_name=f"TSTR_beta{beta}",
            seed=seed,
            max_epochs=50,
            patience=10,
            device=device
        )

        metrics = compute_classification_metrics(tstr_res["targets"], tstr_res["predictions"])
        acc_ts = metrics["accuracy"]
        f1_ts = metrics["macro_f1"]
        delta_pp = 100.0 * (trtr_acc - acc_ts)
        r_ratio = acc_ts / trtr_acc if trtr_acc > 0 else 0.0

        # Đọc lịch sử cVAE để lấy L_rec và L_KL tại best epoch
        with open(cvae_res["history_path"], "r", encoding="utf-8") as f:
            cvae_hist = json.load(f)
        best_ep_idx = cvae_res["best_epoch"] - 1
        rec_loss = cvae_hist["val_rec"][best_ep_idx]
        kl_loss = cvae_hist["val_kl"][best_ep_idx]

        rows.append({
            "Beta": beta,
            "Val Rec Loss": f"{rec_loss:.4f}",
            "Val KL Loss": f"{kl_loss:.4f}",
            "cVAE Best Epoch": cvae_res["best_epoch"],
            "TSTR Accuracy (%)": f"{acc_ts * 100:.2f}",
            "TSTR Macro-F1": f"{f1_ts:.4f}",
            "Delta_pp (so với TRTR)": f"{delta_pp:+.2f}",
            "Tỉ số R": f"{r_ratio:.4f}"
        })

    ablation_df = pd.DataFrame(rows)
    save_path = TABLES_DIR / "ablation_beta_summary.csv"
    ablation_df.to_csv(save_path, index=False)
    print(f"\n-> Bảng kết quả khảo sát Beta đã lưu tại: {save_path}")
    print(ablation_df.to_string(index=False))

    return ablation_df


if __name__ == "__main__":
    run_beta_ablation()
