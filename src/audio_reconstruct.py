"""
Mô-đun khôi phục xấp xỉ âm thanh dạng sóng từ ma trận log-mel bằng Griffin-Lim
theo đúng chỉ dẫn tại mục 5.2 của Đề cương:
1. Hoàn nguyên z-score
2. Đổi dB về công suất mel: M = 10^(L / 10)
3. Bỏ cột thời gian thứ 64 (bổ sung ban đầu -80 dB) -> còn 64 dải x 63 khung
4. Ước lượng phổ STFT và phục hồi pha bằng thuật toán Griffin-Lim (librosa.feature.inverse.mel_to_audio)
Lưu ý: Đây là minh họa nghe thử xấp xỉ, không thay thế đánh giá cảm nhận trực tiếp.
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import soundfile as sf
import librosa
import numpy as np
import torch
from pathlib import Path
from typing import Optional

from .config import OUTPUT_DIR, AudioConfig
from .dataset import load_norm_stats, invert_zscore

AUDIO_OUT_DIR = OUTPUT_DIR / "audio_reconstructed"
AUDIO_OUT_DIR.mkdir(parents=True, exist_ok=True)


def reconstruct_audio_from_logmel(
    x_mel_64x64: np.ndarray,
    output_wav_path: Path,
    cfg: AudioConfig = AudioConfig(),
    n_iter: int = 32
) -> str:
    """
    x_mel_64x64: Mảng NumPy hoặc Tensor [1, 64, 64] hoặc [64, 64] đã chuẩn hóa z-score.
    """
    if isinstance(x_mel_64x64, torch.Tensor):
        x_mel_64x64 = x_mel_64x64.detach().cpu().numpy()

    if x_mel_64x64.ndim == 3 and x_mel_64x64.shape[0] == 1:
        x_mel_64x64 = x_mel_64x64[0]

    mu, sigma = load_norm_stats()

    # 1. Hoàn nguyên z-score về log-mel dB
    L = invert_zscore(x_mel_64x64, mu, sigma)  # [64, 64]

    # 2. Bỏ cột thời gian bổ sung ở cuối (cột thứ 64) -> còn [64, 63]
    L_original_frames = L[:, :63]

    # 3. Đổi dB về công suất Mel (power spectrum)
    # L = 10 * log10(M) -> M = 10^(L / 10)
    mel_power = np.power(10.0, L_original_frames / 10.0)

    # 4. Khôi phục âm thanh bằng Griffin-Lim
    wav = librosa.feature.inverse.mel_to_audio(
        M=mel_power,
        sr=cfg.sample_rate,
        n_fft=cfg.n_fft,
        hop_length=cfg.hop_length,
        win_length=cfg.win_length,
        window=cfg.window,
        center=cfg.center,
        pad_mode=cfg.pad_mode,
        power=cfg.power,
        n_iter=n_iter
    )

    # Chuẩn hóa biên độ để không bị vỡ tiếng khi lưu file
    max_val = np.max(np.abs(wav))
    if max_val > 0:
        wav = wav / max_val * 0.95

    output_wav_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_wav_path), wav, cfg.sample_rate)
    return str(output_wav_path)
