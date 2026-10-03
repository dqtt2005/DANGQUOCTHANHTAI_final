"""
Huấn luyện cVAE (Conditional Variational Autoencoder) theo đúng mục 3.4 của Đề cương:
- Optimizer: Adam, lr=1e-3, weight_decay=0, batch_size=64, drop_last=False, max_epochs=100
- Loss: L_beta = L_rec + beta * L_KL
- Early stopping theo validation loss thấp nhất, patience = 10
- Theo dõi riêng L_rec, L_KL và kiểm tra NaN/Inf
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
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
from typing import Dict, Any, Optional

from .config import (
    PROCESSED_DATA_DIR, CHECKPOINT_DIR, OUTPUT_DIR,
    CVAEConfig
)
from .models.cvae import CVAE
from .loss import CVAELoss


def train_single_cvae(
    beta: float = 1.0,
    latent_dim: int = 32,
    seed: int = 42,
    max_epochs: int = 100,
    patience: int = 10,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
    device: str = "cpu",
    save_prefix: str = "cvae"
) -> Dict[str, Any]:
    # Thiết lập seed cố định
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Nạp dữ liệu đã xử lý
    train_x = torch.load(PROCESSED_DATA_DIR / "train_features.pt")
    train_y = torch.load(PROCESSED_DATA_DIR / "train_labels.pt")
    val_x = torch.load(PROCESSED_DATA_DIR / "val_features.pt")
    val_y = torch.load(PROCESSED_DATA_DIR / "val_labels.pt")

    train_loader = DataLoader(
        TensorDataset(train_x, train_y),
        batch_size=batch_size,
        shuffle=True,
        drop_last=False
    )
    val_loader = DataLoader(
        TensorDataset(val_x, val_y),
        batch_size=batch_size,
        shuffle=False,
        drop_last=False
    )

    device = torch.device(device)
    model = CVAE(in_channels=1, latent_dim=latent_dim, num_classes=10).to(device)
    loss_fn = CVAELoss(beta=beta, num_features=4096)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=0.0)

    # Cố định bộ nhiễu eps để theo dõi trực quan giữa các epoch mà không dùng test
    fixed_noise = torch.randn(10, latent_dim, device=device)
    fixed_labels = torch.arange(10, device=device)

    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    best_weights_path = CHECKPOINT_DIR / f"{save_prefix}_beta{beta}_dz{latent_dim}_seed{seed}.pt"
    history_path = OUTPUT_DIR / f"{save_prefix}_beta{beta}_dz{latent_dim}_seed{seed}_history.json"

    if best_weights_path.exists() and history_path.exists():
        print(f"-> Tái sử dụng cVAE checkpoint có sẵn: {best_weights_path}")
        with open(history_path, "r", encoding="utf-8") as f:
            hist = json.load(f)
        best_val = min(hist["val_loss"])
        best_ep = hist["val_loss"].index(best_val) + 1
        return {
            "checkpoint_path": str(best_weights_path),
            "history_path": str(history_path),
            "best_epoch": best_ep,
            "best_val_loss": best_val,
            "total_time": 0.0
        }

    history = {
        "epoch": [],
        "train_loss": [],
        "train_rec": [],
        "train_kl": [],
        "val_loss": [],
        "val_rec": [],
        "val_kl": [],
        "epoch_time": []
    }

    print(f"\n>>> Bắt đầu huấn luyện cVAE (beta={beta}, d_z={latent_dim}, seed={seed}) <<<")
    start_train_time = time.time()

    for epoch in range(1, max_epochs + 1):
        epoch_start = time.time()
        model.train()
        total_train_loss = 0.0
        total_train_rec = 0.0
        total_train_kl = 0.0
        n_train_batches = 0

        for x_b, y_b in train_loader:
            x_b, y_b = x_b.to(device), y_b.to(device)
            optimizer.zero_grad()

            x_recon, mu, logvar = model(x_b, y_b)
            loss, metrics = loss_fn(x_b, x_recon, mu, logvar, beta=beta)

            if torch.isnan(loss) or torch.isinf(loss):
                raise ValueError(f"Loss NaN/Inf tại epoch {epoch}!")

            loss.backward()
            optimizer.step()

            total_train_loss += metrics["loss_total"]
            total_train_rec += metrics["loss_rec"]
            total_train_kl += metrics["loss_kl"]
            n_train_batches += 1

        avg_train_loss = total_train_loss / n_train_batches
        avg_train_rec = total_train_rec / n_train_batches
        avg_train_kl = total_train_kl / n_train_batches

        # Đánh giá trên Validation
        model.eval()
        total_val_loss = 0.0
        total_val_rec = 0.0
        total_val_kl = 0.0
        n_val_batches = 0

        with torch.no_grad():
            for x_v, y_v in val_loader:
                x_v, y_v = x_v.to(device), y_v.to(device)
                # Khi eval, reparameterize trả về mu
                c_onehot = model.to_onehot(y_v)
                mu_v, logvar_v = model.encoder(x_v, c_onehot)
                x_recon_v = model.decoder(mu_v, c_onehot)
                v_loss, v_metrics = loss_fn(x_v, x_recon_v, mu_v, logvar_v, beta=beta)

                total_val_loss += v_metrics["loss_total"]
                total_val_rec += v_metrics["loss_rec"]
                total_val_kl += v_metrics["loss_kl"]
                n_val_batches += 1

        avg_val_loss = total_val_loss / n_val_batches
        avg_val_rec = total_val_rec / n_val_batches
        avg_val_kl = total_val_kl / n_val_batches
        epoch_dur = time.time() - epoch_start

        history["epoch"].append(epoch)
        history["train_loss"].append(avg_train_loss)
        history["train_rec"].append(avg_train_rec)
        history["train_kl"].append(avg_train_kl)
        history["val_loss"].append(avg_val_loss)
        history["val_rec"].append(avg_val_rec)
        history["val_kl"].append(avg_val_kl)
        history["epoch_time"].append(epoch_dur)

        if epoch % 5 == 0 or epoch == 1:
            print(f"Epoch {epoch:03d}/{max_epochs:03d} [{epoch_dur:.1f}s] - "
                  f"Train Loss: {avg_train_loss:.4f} (Rec: {avg_train_rec:.4f}, KL: {avg_train_kl:.4f}) | "
                  f"Val Loss: {avg_val_loss:.4f} (Rec: {avg_val_rec:.4f}, KL: {avg_val_kl:.4f})")

        # Early stopping theo val_loss
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            patience_counter = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": avg_val_loss,
                "beta": beta,
                "latent_dim": latent_dim,
                "seed": seed
            }, best_weights_path)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"-> Early stopping tại epoch {epoch} (Best epoch: {best_epoch}, Val Loss: {best_val_loss:.4f})")
                break

    total_time = time.time() - start_train_time
    print(f"-> Hoàn tất cVAE trong {total_time:.2f}s. Checkpoint tốt nhất tại: {best_weights_path}")

    # Lưu lịch sử huấn luyện
    history_path = OUTPUT_DIR / f"{save_prefix}_beta{beta}_dz{latent_dim}_seed{seed}_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return {
        "checkpoint_path": str(best_weights_path),
        "history_path": str(history_path),
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "total_time": total_time
    }


if __name__ == "__main__":
    train_single_cvae(beta=1.0, latent_dim=32, seed=42)
