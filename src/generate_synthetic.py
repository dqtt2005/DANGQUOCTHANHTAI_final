"""
Sinh tập đặc trưng tổng hợp cân bằng từ cVAE theo đúng mục 4.2 của Đề cương:
- z ~ N(0, I) độc lập
- 240 mẫu cho mỗi nhãn c in {0, ..., 9} -> Tổng cộng 2.400 mẫu cân bằng
- Sử dụng x_syn = f_theta(z, c) (đầu ra Decoder, không thêm nhiễu quan sát)
- Không dùng phổ tái tạo của ảnh thật, không lọc mẫu bằng classifier
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import torch
from pathlib import Path
from typing import Tuple

from .config import (
    CHECKPOINT_DIR, OUTPUT_DIR, PROCESSED_DATA_DIR
)
from .models.cvae import CVAE


def generate_synthetic_dataset(
    cvae_checkpoint_path: Path,
    num_samples_per_class: int = 240,
    num_classes: int = 10,
    seed: int = 42,
    device: str = "cpu",
    output_prefix: str = "synthetic"
) -> Tuple[torch.Tensor, torch.Tensor, Path]:
    """
    Sinh 2.400 mẫu tổng hợp (240 mẫu/lớp) từ mô hình cVAE đã huấn luyện.
    """
    save_path = PROCESSED_DATA_DIR / f"{output_prefix}_samples_seed{seed}.pt"
    if save_path.exists():
        print(f"-> Tái sử dụng tập dữ liệu tổng hợp có sẵn: {save_path}")
        cached = torch.load(save_path)
        return cached["features"], cached["labels"], save_path

    torch.manual_seed(seed)
    device = torch.device(device)

    # Nạp checkpoint
    checkpoint = torch.load(cvae_checkpoint_path, map_location=device)
    latent_dim = checkpoint.get("latent_dim", 32)
    model = CVAE(in_channels=1, latent_dim=latent_dim, num_classes=num_classes).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    all_features = []
    all_labels = []

    print(f"\n>>> Đang sinh {num_samples_per_class * num_classes} mẫu tổng hợp ({num_samples_per_class} mẫu/lớp) từ prior N(0, I) <<<")

    with torch.no_grad():
        for digit in range(num_classes):
            # Nhãn điều kiện yêu cầu
            labels = torch.full((num_samples_per_class,), digit, dtype=torch.long, device=device)
            # Lấy mẫu z độc lập từ phân phối chuẩn tắc N(0, I)
            z = torch.randn(num_samples_per_class, latent_dim, device=device)
            c_onehot = model.to_onehot(labels)
            # Qua Decoder để sinh đặc trưng x_syn
            x_syn = model.decoder(z, c_onehot)

            all_features.append(x_syn.cpu())
            all_labels.append(labels.cpu())

    features_tensor = torch.cat(all_features, dim=0)  # [N_syn, 1, 64, 64]
    labels_tensor = torch.cat(all_labels, dim=0)      # [N_syn]

    # Kiểm tra tính toàn vẹn
    assert features_tensor.shape == (num_samples_per_class * num_classes, 1, 64, 64)
    assert not torch.isnan(features_tensor).any(), "Mẫu sinh chứa NaN!"
    assert not torch.isinf(features_tensor).any(), "Mẫu sinh chứa Inf!"

    # Lưu tập tổng hợp
    save_path = PROCESSED_DATA_DIR / f"{output_prefix}_samples_seed{seed}.pt"
    torch.save({
        "features": features_tensor,
        "labels": labels_tensor,
        "seed": seed,
        "latent_dim": latent_dim,
        "num_samples_per_class": num_samples_per_class,
        "source_checkpoint": str(cvae_checkpoint_path)
    }, save_path)

    print(f"-> Đã lưu tập dữ liệu tổng hợp tại: {save_path}")
    print(f"   Kích thước tensor: {features_tensor.shape}, Số lượng nhãn: {labels_tensor.shape}")

    return features_tensor, labels_tensor, save_path


if __name__ == "__main__":
    ckpt = CHECKPOINT_DIR / "cvae_beta1.0_dz32_seed42.pt"
    if ckpt.exists():
        generate_synthetic_dataset(ckpt, seed=42)
    else:
        print(f"Chưa có checkpoint {ckpt}, hãy chạy huấn luyện cVAE trước.")
