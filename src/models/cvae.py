"""
Mô hình cVAE (Conditional Variational Autoencoder) theo đúng đặc tả Bảng 2 trong Đề cương.
Encoder 4 tầng Conv2D, Decoder 4 tầng ConvTranspose2D, điều kiện one-hot 10 lớp nối ở cả hai phía.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class Encoder(nn.Module):
    def __init__(self, in_channels: int = 1, latent_dim: int = 32, num_classes: int = 10):
        super().__init__()
        self.latent_dim = latent_dim
        self.num_classes = num_classes

        # [B, 1, 64, 64] -> [B, 32, 32, 32] -> [B, 64, 16, 16] -> [B, 128, 8, 8] -> [B, 256, 4, 4]
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, kernel_size=4, stride=2, padding=1),
            nn.ReLU(inplace=True),
        )

        # Flatten 256 * 4 * 4 = 4096. Nối one-hot 10 chiều -> 4106
        self.fc_mu = nn.Linear(4096 + num_classes, latent_dim)
        self.fc_logvar = nn.Linear(4096 + num_classes, latent_dim)

    def forward(self, x: torch.Tensor, c_onehot: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.conv(x)  # [B, 256, 4, 4]
        h_flat = h.view(h.size(0), -1)  # [B, 4096]
        h_cond = torch.cat([h_flat, c_onehot], dim=1)  # [B, 4106]
        mu = self.fc_mu(h_cond)  # [B, latent_dim]
        logvar = self.fc_logvar(h_cond)  # [B, latent_dim] (ell = log(sigma^2))
        return mu, logvar


class Decoder(nn.Module):
    def __init__(self, latent_dim: int = 32, num_classes: int = 10, out_channels: int = 1):
        super().__init__()
        self.latent_dim = latent_dim
        self.num_classes = num_classes

        # Nối z và one-hot: latent_dim + num_classes -> 4096
        self.fc = nn.Sequential(
            nn.Linear(latent_dim + num_classes, 4096),
            nn.ReLU(inplace=True)
        )

        # Reshape [B, 256, 4, 4] -> [B, 128, 8, 8] -> [B, 64, 16, 16] -> [B, 32, 32, 32] -> [B, 1, 64, 64]
        self.deconv = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1, output_padding=0),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1, output_padding=0),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1, output_padding=0),
            nn.ReLU(inplace=True),
            # Tầng cuối tuyến tính, không dùng Sigmoid/Tanh vì x đã chuẩn hóa z-score
            nn.ConvTranspose2d(32, out_channels, kernel_size=4, stride=2, padding=1, output_padding=0),
        )

    def forward(self, z: torch.Tensor, c_onehot: torch.Tensor) -> torch.Tensor:
        h_cond = torch.cat([z, c_onehot], dim=1)  # [B, latent_dim + num_classes]
        h = self.fc(h_cond)  # [B, 4096]
        h = h.view(h.size(0), 256, 4, 4)  # [B, 256, 4, 4]
        x_recon = self.deconv(h)  # [B, 1, 64, 64]
        return x_recon


class CVAE(nn.Module):
    def __init__(
        self,
        in_channels: int = 1,
        latent_dim: int = 32,
        num_classes: int = 10,
        out_channels: int = 1
    ):
        super().__init__()
        self.latent_dim = latent_dim
        self.num_classes = num_classes
        self.encoder = Encoder(in_channels=in_channels, latent_dim=latent_dim, num_classes=num_classes)
        self.decoder = Decoder(latent_dim=latent_dim, num_classes=num_classes, out_channels=out_channels)

    def to_onehot(self, c: torch.Tensor) -> torch.Tensor:
        if c.dim() == 1:
            return F.one_hot(c, num_classes=self.num_classes).float()
        return c.float()

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """
        Tái tham số hóa: z = mu + exp(ell / 2) * eps, eps ~ N(0, I)
        """
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        else:
            return mu

    def forward(self, x: torch.Tensor, c: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        c_onehot = self.to_onehot(c)
        mu, logvar = self.encoder(x, c_onehot)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decoder(z, c_onehot)
        return x_recon, mu, logvar

    @torch.no_grad()
    def sample(self, c: torch.Tensor, device: torch.device = None) -> torch.Tensor:
        """
        Sinh đặc trưng mới từ phân phối tiên nghiệm z ~ N(0, I).
        x_syn = f_theta(z, c)
        """
        self.eval()
        if device is None:
            device = next(self.parameters()).device

        c_onehot = self.to_onehot(c).to(device)
        batch_size = c_onehot.size(0)
        z = torch.randn(batch_size, self.latent_dim, device=device)
        x_syn = self.decoder(z, c_onehot)
        return x_syn
