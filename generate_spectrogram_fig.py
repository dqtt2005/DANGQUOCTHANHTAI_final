import matplotlib.pyplot as plt
import numpy as np
import librosa
from pathlib import Path

raw_dir = Path("data/raw/fsdd/recordings")
digits = range(10)
fig, axes = plt.subplots(2, 5, figsize=(14, 6))
axes = axes.flatten()

for digit in digits:
    fnames = list(raw_dir.glob(f"{digit}_jackson_*.wav")) or list(raw_dir.glob(f"{digit}_*.wav"))
    if fnames:
        y, sr = librosa.load(str(fnames[0]), sr=8000)
        if len(y) < 8000:
            y = np.pad(y, (0, 8000 - len(y)))
        else:
            mid = len(y) // 2
            y = y[mid - 4000:mid + 4000]
        mel = librosa.feature.melspectrogram(
            y=y, sr=8000, n_fft=256, hop_length=128, n_mels=64,
            fmin=0, fmax=4000, power=2, norm='slaney'
        )
        mel_db = 10.0 * np.log10(np.maximum(mel, 1e-8))
        mel_db_64 = np.pad(mel_db, ((0, 0), (0, 1)), mode='constant', constant_values=-80.0)
        im = axes[digit].imshow(mel_db_64, aspect='auto', origin='lower', cmap='viridis')
        axes[digit].set_title(f"Chữ số {digit} ({fnames[0].name})", fontsize=10, fontweight='bold')
        axes[digit].set_xlabel("Khung (64)", fontsize=8)
        axes[digit].set_ylabel("Mel (64)", fontsize=8)

plt.tight_layout()
Path("outputs/figures").mkdir(parents=True, exist_ok=True)
plt.savefig("outputs/figures/spectrogram_sample_digits.png", dpi=200, bbox_inches='tight')
plt.close()
print("Generated outputs/figures/spectrogram_sample_digits.png successfully")
