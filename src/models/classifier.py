"""
Bộ phân loại chữ số nói (Classifier) dùng chung cho cả đối chuẩn TRTR và TSTR.
Kiến trúc 3 khối Conv2D-ReLU-MaxPool, AdaptiveAvgPool2D(4x4), Dense(1024->64->10).
Tuân thủ nghiêm ngặt mục 4.1 của Đề cương.
"""

import torch
import torch.nn as nn


class AudioClassifier(nn.Module):
    def __init__(self, in_channels: int = 1, num_classes: int = 10, dropout_rate: float = 0.2):
        super().__init__()
        # Ba khối Conv2D -> ReLU -> MaxPool2D (kênh: 1 -> 16 -> 32 -> 64)
        self.features = nn.Sequential(
            # Khối 1: [B, 1, 64, 64] -> [B, 16, 32, 32]
            nn.Conv2d(in_channels, 16, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),

            # Khối 2: [B, 16, 32, 32] -> [B, 32, 16, 16]
            nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),

            # Khối 3: [B, 32, 16, 16] -> [B, 64, 8, 8]
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )

        # AdaptiveAvgPool2D(4 x 4) -> Flatten 64 * 4 * 4 = 1024 chiều
        self.avgpool = nn.AdaptiveAvgPool2d((4, 4))

        # Phân loại: Linear(1024, 64) -> ReLU -> Dropout(0.2) -> Linear(64, 10)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),
            nn.Linear(64, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: [B, 1, 64, 64]
        returns: logits [B, 10]
        """
        feats = self.features(x)
        pooled = self.avgpool(feats)
        logits = self.classifier(pooled)
        return logits
