"""
Pipeline thực nghiệm toàn diện (Master Execution Script) cho đề tài:
"Sinh đặc trưng log-mel của chữ số nói bằng cVAE và đánh giá theo giao thức TSTR"
Đề cương: Đặng Quốc Thành Tài - MSSV 23110149 - G1
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import time
import json
import torch
import numpy as np
import pandas as pd
from pathlib import Path

from .config import (
    PROCESSED_DATA_DIR, CHECKPOINT_DIR, OUTPUT_DIR, FIGURES_DIR,
    TABLES_DIR, PREDICTIONS_DIR, EXPORT_DIR, AudioConfig
)
from .train_cvae import train_single_cvae
from .generate_synthetic import generate_synthetic_dataset
from .train_classifier import train_single_classifier
from .models.classifier import AudioClassifier
from .models.cvae import CVAE
from .evaluate import (
    compute_classification_metrics, summarize_paired_experiments,
    plot_confusion_matrices, plot_spectrogram_triplet
)
from .ablation_beta import run_beta_ablation
from .benchmark_cost import run_all_benchmarks
from .esp32_export import export_all_models_for_esp32
from .audio_reconstruct import reconstruct_audio_from_logmel


def main():
    print("==========================================================================")
    print("KHỞI CHẠY TOÀN BỘ PIPELINE THỰC NGHIỆM KHOA HỌC (G1 - ĐẶNG QUỐC THÀNH TÀI)")
    print("==========================================================================\n")
    pipeline_start = time.time()

    # Nạp dữ liệu đã xử lý
    train_x = torch.load(PROCESSED_DATA_DIR / "train_features.pt")
    train_y = torch.load(PROCESSED_DATA_DIR / "train_labels.pt")
    val_x = torch.load(PROCESSED_DATA_DIR / "val_features.pt")
    val_y = torch.load(PROCESSED_DATA_DIR / "val_labels.pt")
    test_x = torch.load(PROCESSED_DATA_DIR / "test_features.pt")
    test_y = torch.load(PROCESSED_DATA_DIR / "test_labels.pt")

    seeds = [7, 42, 2026]
    trtr_results = []
    tstr_results = []

    print("\n-------------------------------------------------------------")
    print("GIAI ĐOẠN 1: HUẤN LUYỆN VÀ ĐỐI CHUẨN TRTR & TSTR TRÊN 3 SEED")
    print("-------------------------------------------------------------")

    for seed in seeds:
        print(f"\n===================>>> THỰC NGHIỆM VỚI SEED: {seed} <<<===================")

        # 1. Khởi tạo classifier cố định theo seed để ghép cặp so sánh
        torch.manual_seed(seed)
        initial_classifier = AudioClassifier(in_channels=1, num_classes=10)

        # 2. Huấn luyện Classifier TRTR (Train on Real: 2400 mẫu thật)
        print(f"\n[Seed {seed}] Huấn luyện TRTR Classifier...")
        trtr_res = train_single_classifier(
            train_x=train_x,
            train_y=train_y,
            val_x=val_x,
            val_y=val_y,
            test_x=test_x,
            test_y=test_y,
            initial_model=initial_classifier,
            mode_name="TRTR",
            seed=seed,
            max_epochs=50,
            patience=10
        )
        trtr_metrics = compute_classification_metrics(trtr_res["targets"], trtr_res["predictions"])
        trtr_res.update(trtr_metrics)
        trtr_results.append(trtr_res)
        print(f"-> [TRTR Seed {seed}] Test Accuracy: {trtr_res['test_acc']*100:.2f}%, Macro-F1: {trtr_res['macro_f1']:.4f}")

        # 3. Huấn luyện cVAE (beta=1.0, d_z=32)
        print(f"\n[Seed {seed}] Huấn luyện cVAE (beta=1.0)...")
        cvae_res = train_single_cvae(
            beta=1.0,
            latent_dim=32,
            seed=seed,
            max_epochs=100,
            patience=10
        )

        # 4. Sinh tập tổng hợp TSTR từ prior z ~ N(0, I) (240 mẫu/lớp x 10 = 2400 mẫu)
        print(f"\n[Seed {seed}] Sinh 2.400 mẫu tổng hợp từ prior...")
        syn_x, syn_y, syn_path = generate_synthetic_dataset(
            cvae_checkpoint_path=Path(cvae_res["checkpoint_path"]),
            num_samples_per_class=240,
            seed=seed,
            output_prefix=f"synthetic_main"
        )

        # 5. Huấn luyện Classifier TSTR (Train on Synthetic: 2400 mẫu sinh)
        print(f"\n[Seed {seed}] Huấn luyện TSTR Classifier (Khởi tạo cùng trọng số với TRTR)...")
        tstr_res = train_single_classifier(
            train_x=syn_x,
            train_y=syn_y,
            val_x=val_x,
            val_y=val_y,
            test_x=test_x,
            test_y=test_y,
            initial_model=initial_classifier,
            mode_name="TSTR",
            seed=seed,
            max_epochs=50,
            patience=10
        )
        tstr_metrics = compute_classification_metrics(tstr_res["targets"], tstr_res["predictions"])
        tstr_res.update(tstr_metrics)
        tstr_results.append(tstr_res)
        print(f"-> [TSTR Seed {seed}] Test Accuracy: {tstr_res['test_acc']*100:.2f}%, Macro-F1: {tstr_res['macro_f1']:.4f}")

    # Tổng hợp bảng TRTR vs TSTR
    print("\n-------------------------------------------------------------")
    print("TỔNG HỢP VÀ BÁO CÁO KẾT QUẢ SO SÁNH GHÉP CẶP TRTR vs TSTR")
    print("-------------------------------------------------------------")
    summary_df = summarize_paired_experiments(trtr_results, tstr_results, seeds)

    # Vẽ ma trận nhầm lẫn cho seed đại diện (seed 42)
    seed42_idx = seeds.index(42)
    cm_trtr = np.array(trtr_results[seed42_idx]["confusion_matrix_norm"])
    cm_tstr = np.array(tstr_results[seed42_idx]["confusion_matrix_norm"])
    plot_confusion_matrices(cm_trtr, cm_tstr, FIGURES_DIR / "confusion_matrix_trtr_vs_tstr_seed42.png")

    # Vẽ phổ đối sánh thật vs tái tạo vs sinh từ prior cho các chữ số
    cvae_ckpt42 = torch.load(CHECKPOINT_DIR / "cvae_beta1.0_dz32_seed42.pt", map_location="cpu")
    cvae_eval = CVAE(in_channels=1, latent_dim=32, num_classes=10)
    cvae_eval.load_state_dict(cvae_ckpt42["model_state_dict"])
    cvae_eval.eval()

    with torch.no_grad():
        for digit in [0, 1, 5, 7]:
            # Tìm mẫu thật đầu tiên của digit trong tập test
            mask = (test_y == digit)
            idx = torch.nonzero(mask)[0].item()
            real_sample = test_x[idx : idx + 1]  # [1, 1, 64, 64]

            # Mẫu tái tạo
            c_onehot = cvae_eval.to_onehot(torch.tensor([digit]))
            mu, _ = cvae_eval.encoder(real_sample, c_onehot)
            recon_sample = cvae_eval.decoder(mu, c_onehot)

            # Mẫu sinh từ prior
            z_sample = torch.randn(1, 32)
            syn_sample = cvae_eval.decoder(z_sample, c_onehot)

            plot_spectrogram_triplet(
                real_sample=real_sample[0].numpy(),
                recon_sample=recon_sample[0].numpy(),
                syn_sample=syn_sample[0].numpy(),
                digit=digit,
                save_path=FIGURES_DIR / f"spectrogram_comparison_digit_{digit}.png"
            )

    # 6. Khảo sát độ nhạy Beta in {0, 0.1, 1.0} trên seed 42
    print("\n-------------------------------------------------------------")
    print("GIAI ĐOẠN 2: THÍ NGHIỆM KHẢO SÁT ĐỘ NHẠY TRỌNG SỐ BETA")
    print("-------------------------------------------------------------")
    run_beta_ablation(beta_list=[0.0, 0.1, 1.0], seed=42)

    # 7. Đo lường chi phí tính toán (Benchmark)
    print("\n-------------------------------------------------------------")
    print("GIAI ĐOẠN 3: ĐO LƯỜNG CHI PHÍ TÍNH TOÁN (BENCHMARK)")
    print("-------------------------------------------------------------")
    manifest_df = pd.read_csv(PROCESSED_DATA_DIR.parent / "manifests" / "manifest.csv")
    sample_wav = manifest_df.iloc[0]["file_path"]
    run_all_benchmarks(sample_wav)

    # 8. Đóng gói xuất mô hình phục vụ nạp ESP32
    print("\n-------------------------------------------------------------")
    print("GIAI ĐOẠN 4: ĐÓNG GÓI VÀ XUẤT MÔ HÌNH CHO ESP32 (TINYML READY)")
    print("-------------------------------------------------------------")
    export_all_models_for_esp32()

    # 9. Khôi phục âm thanh nghe thử minh họa bằng Griffin-Lim
    print("\n-------------------------------------------------------------")
    print("GIAI ĐOẠN 5: KHÔI PHỤC ÂM THANH NGHE THỬ (GRIFFIN-LIM)")
    print("-------------------------------------------------------------")
    for digit in [0, 1, 7]:
        c_onehot = cvae_eval.to_onehot(torch.tensor([digit]))
        z_sample = torch.randn(1, 32)
        syn_sample = cvae_eval.decoder(z_sample, c_onehot)
        wav_path = reconstruct_audio_from_logmel(
            syn_sample[0].numpy(),
            OUTPUT_DIR / "audio_reconstructed" / f"synth_digit_{digit}.wav"
        )
        print(f"-> Đã xuất file âm thanh nghe thử chữ số {digit}: {wav_path}")

    total_pipeline_time = time.time() - pipeline_start
    print(f"\n==========================================================================")
    print(f"TOÀN BỘ PIPELINE ĐÃ HOÀN THÀNH THÀNH CÔNG TRONG: {total_pipeline_time:.2f} giây ({total_pipeline_time/60.0:.2f} phút)!")
    print("==========================================================================\n")


if __name__ == "__main__":
    main()
