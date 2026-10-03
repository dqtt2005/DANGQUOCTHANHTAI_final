"""
Huấn luyện Classifier cho TRTR và TSTR theo phương pháp ghép cặp (Paired Comparison)
quy định tại mục 4.1, 4.2, 4.3 của Đề cương:
- Ba seed chính: 7, 42, 2026
- Trong mỗi seed, hai classifier được khởi tạo cùng trọng số ban đầu
- TRTR: Huấn luyện trên 2.400 mẫu thật
- TSTR: Huấn luyện trên 2.400 mẫu cVAE tổng hợp (240 mẫu/lớp)
- Cả hai dùng chung 300 mẫu validation thật để chọn checkpoint (Early Stopping patience=10)
- Đánh giá trên cùng 300 mẫu test thật, lưu dự đoán từng mẫu
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import copy
import time
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
from typing import Dict, Any, Tuple, List
import pandas as pd

from .config import (
    PROCESSED_DATA_DIR, CHECKPOINT_DIR, OUTPUT_DIR, PREDICTIONS_DIR,
    ClassifierConfig
)
from .models.classifier import AudioClassifier


def train_single_classifier(
    train_x: torch.Tensor,
    train_y: torch.Tensor,
    val_x: torch.Tensor,
    val_y: torch.Tensor,
    test_x: torch.Tensor,
    test_y: torch.Tensor,
    initial_model: AudioClassifier,
    mode_name: str = "TRTR",
    seed: int = 42,
    max_epochs: int = 50,
    patience: int = 10,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
    device: str = "cpu"
) -> Dict[str, Any]:
    device = torch.device(device)
    model = copy.deepcopy(initial_model).to(device)

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
    test_loader = DataLoader(
        TensorDataset(test_x, test_y),
        batch_size=batch_size,
        shuffle=False,
        drop_last=False
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=0.0)

    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    best_weights_path = CHECKPOINT_DIR / f"classifier_{mode_name.lower()}_seed{seed}.pt"
    pred_path = PREDICTIONS_DIR / f"preds_{mode_name.lower()}_seed{seed}.csv"

    # Tái sử dụng kết quả đã lưu nếu có sẵn
    if best_weights_path.exists() and pred_path.exists():
        print(f"[{mode_name} Seed {seed}] Tái sử dụng checkpoint có sẵn: {best_weights_path}")
        best_ckpt = torch.load(best_weights_path, map_location=device)
        pred_df = pd.read_csv(pred_path)
        all_targets = pred_df["true_label"].tolist()
        all_preds = pred_df["predicted_label"].tolist()
        test_acc = float((pred_df["is_correct"] == True).mean())
        return {
            "mode": mode_name,
            "seed": seed,
            "best_epoch": best_ckpt.get("epoch", 0),
            "val_loss": best_ckpt.get("val_loss", 0.0),
            "val_acc": best_ckpt.get("val_acc", 0.0),
            "test_acc": test_acc,
            "checkpoint_path": str(best_weights_path),
            "pred_path": str(pred_path),
            "targets": all_targets,
            "predictions": all_preds,
            "train_time": 0.0
        }

    history = {
        "epoch": [],
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": [],
        "epoch_time": []
    }

    start_time = time.time()
    for epoch in range(1, max_epochs + 1):
        ep_start = time.time()
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(yb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += len(yb)

        train_loss = total_loss / total
        train_acc = correct / total

        # Đánh giá trên Validation thật
        model.eval()
        v_loss = 0.0
        v_correct = 0
        v_total = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                logits = model(xb)
                loss = criterion(logits, yb)
                v_loss += loss.item() * len(yb)
                preds = logits.argmax(dim=1)
                v_correct += (preds == yb).sum().item()
                v_total += len(yb)

        val_loss = v_loss / v_total
        val_acc = v_correct / v_total
        dur = time.time() - ep_start

        history["epoch"].append(epoch)
        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["epoch_time"].append(dur)

        if epoch % 5 == 0 or epoch == 1:
            print(f"[{mode_name} Seed {seed}] Ep {epoch:02d}/{max_epochs} - Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}%")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_loss": val_loss,
                "val_acc": val_acc,
                "mode": mode_name,
                "seed": seed
            }, best_weights_path)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"[{mode_name} Seed {seed}] Early stopping tại epoch {epoch} (Best: {best_epoch}, Val Loss: {best_val_loss:.4f})")
                break

    # Đánh giá trên Test thật bằng checkpoint tốt nhất
    best_ckpt = torch.load(best_weights_path, map_location=device)
    model.load_state_dict(best_ckpt["model_state_dict"])
    model.eval()

    all_preds = []
    all_targets = []
    all_logits = []

    with torch.no_grad():
        for xb, yb in test_loader:
            xb = xb.to(device)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            all_preds.extend(preds.cpu().tolist())
            all_targets.extend(yb.tolist())
            all_logits.append(logits.cpu())

    all_logits = torch.cat(all_logits, dim=0).numpy()
    test_acc = sum([p == t for p, t in zip(all_preds, all_targets)]) / len(all_targets)

    # Lưu dự đoán từng mẫu
    pred_df = pd.DataFrame({
        "sample_index": list(range(len(all_targets))),
        "true_label": all_targets,
        "predicted_label": all_preds,
        "is_correct": [p == t for p, t in zip(all_preds, all_targets)]
    })
    pred_path = PREDICTIONS_DIR / f"preds_{mode_name.lower()}_seed{seed}.csv"
    pred_df.to_csv(pred_path, index=False)

    return {
        "mode": mode_name,
        "seed": seed,
        "best_epoch": best_epoch,
        "val_loss": best_val_loss,
        "val_acc": best_ckpt["val_acc"],
        "test_acc": test_acc,
        "checkpoint_path": str(best_weights_path),
        "pred_path": str(pred_path),
        "history": history,
        "targets": all_targets,
        "predictions": all_preds,
        "logits": all_logits,
        "train_time": time.time() - start_time
    }
