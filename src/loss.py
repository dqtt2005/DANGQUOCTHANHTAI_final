"""
Định nghĩa hàm mất mát Conditional ELBO cho cVAE theo đúng công thức Đề cương:
L_rec = 1/(2B) * sum_{i=1}^B sum_{k=1}^D (x_ik - x_hat_ik)^2
L_KL  = 1/(2B) * sum_{i=1}^B sum_{j=1}^{d_z} (mu_ij^2 + exp(ell_ij) - 1 - ell_ij)
L_beta = L_rec + beta * L_KL
"""

import torch
import torch.nn as nn
from typing import Tuple, Dict


class CVAELoss(nn.Module):
    def __init__(self, beta: float = 1.0, num_features: int = 4096):
        super().__init__()
        self.beta = beta
        self.num_features = num_features

    def forward(
        self,
        x: torch.Tensor,
        x_recon: torch.Tensor,
        mu: torch.Tensor,
        log_var: torch.Tensor,
        beta: float = None
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        x: Tensor thật [B, 1, 64, 64]
        x_recon: Tensor tái tạo [B, 1, 64, 64]
        mu: [B, d_z]
        log_var: [B, d_z] (ell = log(sigma^2))
        beta: Trọng số KL (nếu truyền vào sẽ ghi đè self.beta)
        """
        if beta is None:
            beta = self.beta

        # B là kích thước batch
        # 1. Sai số tái tạo: sum theo các chiều không gian [1, 2, 3] cho từng mẫu, sau đó lấy trung bình theo batch
        # L_rec = 1/(2B) * sum_{i=1}^B sum_{k=1}^D (x_ik - x_hat_ik)^2
        diff_sq = (x - x_recon).pow(2)  # [B, 1, 64, 64]
        sum_sq_per_sample = diff_sq.view(x.size(0), -1).sum(dim=1)  # [B]
        l_rec = 0.5 * sum_sq_per_sample.mean()

        # 2. Sai số KL: sum theo d_z cho từng mẫu, sau đó lấy trung bình theo batch
        # L_KL = 1/(2B) * sum_{i=1}^B sum_{j=1}^{d_z} (mu_ij^2 + exp(ell_ij) - 1 - ell_ij)
        kl_per_sample = (mu.pow(2) + torch.exp(log_var) - 1.0 - log_var).sum(dim=1)  # [B]
        l_kl = 0.5 * kl_per_sample.mean()

        # 3. Tổng mất mát có trọng số beta
        l_beta = l_rec + beta * l_kl

        # MSE trên từng phần tử: 2 * L_rec / D
        mse_per_element = (2.0 * l_rec / self.num_features).item()

        metrics = {
            "loss_total": l_beta.item(),
            "loss_rec": l_rec.item(),
            "loss_kl": l_kl.item(),
            "mse_per_element": mse_per_element,
            "beta": beta
        }

        return l_beta, metrics
