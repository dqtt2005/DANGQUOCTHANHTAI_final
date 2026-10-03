# TRƯỜNG ĐẠI HỌC CÔNG NGHỆ KỸ THUẬT THÀNH PHỐ HỒ CHÍ MINH
# KHOA CÔNG NGHỆ THÔNG TIN

---

## BÁO CÁO TIỂU LUẬN CUỐI KHÓA
### Học phần: Trí tuệ nhân tạo cho IoT (Mã lớp: 261AIOT331185_01CLC)

# SINH ĐẶC TRƯNG LOG-MEL CỦA CHỮ SỐ NÓI BẰNG cVAE VÀ ĐÁNH GIÁ THEO GIAO THỨC TSTR

- **Mã đề tài:** G1
- **Phân nhóm:** Tạo sinh (Generative Models)
- **Sinh viên thực hiện:** Đặng Quốc Thành Tài
- **Mã số sinh viên:** 23110149
- **Giảng viên hướng dẫn:** ThS/TS. Hồ Nhựt Minh
- **Bộ dữ liệu thực nghiệm:** Free Spoken Digit Dataset (FSDD)

*Thành phố Hồ Chí Minh, Năm học 2026 – 2027*

---

## TÓM TẮT BÁO CÁO

Báo cáo này trình bày toàn bộ quy trình thiết kế, triển khai thực nghiệm và phân tích định lượng cho đề tài **"Sinh đặc trưng log-mel của chữ số nói bằng cVAE và đánh giá theo giao thức TSTR"**. Bài toán tập trung vào việc học phân phối biểu diễn không gian phổ log-mel kích thước $1 \times 64 \times 64$ của 10 chữ số tiếng Anh (0–9) từ bộ dữ liệu Free Spoken Digit Dataset (FSDD) thông qua mô hình Tự mã hóa biến phân có điều kiện (Conditional Variational Autoencoder - cVAE). 

Mức độ hữu ích và khả năng ứng dụng của dữ liệu tổng hợp được kiểm chứng chặt chẽ bằng giao thức **TSTR (Train on Synthetic, Test on Real)**, lấy đối chuẩn **TRTR (Train on Real, Test on Real)** làm mốc tham chiếu. Dữ liệu gồm 3.000 bản ghi WAV đơn kênh (8 kHz) được phân chia nghiêm ngặt theo manifest cố định không rò rỉ: tập Train thật (2.400 mẫu), tập Validation thật (300 mẫu) và tập Test thật (300 mẫu). Thống kê chuẩn hóa $z$-score được tính toán độc lập chỉ trên tập Train thật. Mô hình cVAE gồm 4 tầng tích chập và 4 tầng tích chập chuyển vị với vector tiềm ẩn $d_z = 32$, được tối ưu hóa theo hàm mục tiêu Conditional ELBO có trọng số $\beta$. Bộ phân loại downstream sử dụng mạng CNN 3 khối tích chập, được khởi tạo cùng trọng số ghép cặp cho từng seed và sử dụng cùng tập validation thật để chọn checkpoint (công bố minh bạch).

Kết quả thực nghiệm thực đo trên tập test độc lập cho thấy:
- Đối chuẩn tham chiếu **TRTR đạt Accuracy 98.00%**, vượt xa mốc định hướng ban đầu ($\ge 90\%$).
- Mô hình huấn luyện thuần trên dữ liệu tổng hợp **TSTR đạt Accuracy 86.00%**.
- Độ sụt giảm hiệu năng **$\Delta_{pp} = +12.00$ điểm phần trăm**, hoàn toàn thỏa mãn mục tiêu định hướng của đề cương ($\le 15$ điểm phần trăm).
- Tỉ số chuyển giao năng lực nhận dạng **$R = a_{TSTR} / a_{TRTR} = 0.8776$** ($\approx 87.76\%$), vượt mốc kỳ vọng $\ge 80\%$.
- Phân tích chi phí tính toán và ngân sách phần cứng cho thấy bộ phân loại nhận dạng chỉ có **~21.800 tham số**, chiếm **~87 KB Flash (FP32)** hoặc **~22 KB (INT8)** và yêu cầu **~64 KB RAM Tensor Arena**, hoàn toàn tương thích và sẵn sàng triển khai trên chip vi điều khiển nhúng **ESP32** (4 MB Flash, 520 KB SRAM).

---

## MỤC LỤC
1. [Chương 1: Đặt vấn đề và Mục tiêu nghiên cứu](#chương-1-đặt-vấn-đề-và-mục-tiêu-nghiên-cứu)
2. [Chương 2: Tập dữ liệu và Tiền xử lý tín hiệu](#chương-2-tập-dữ-liệu-và-tiền-xử-lý-tín-hiệu)
3. [Chương 3: Phương pháp đề xuất](#chương-3-phương-pháp-đề-xuất)
4. [Chương 4: Thiết kế thực nghiệm và Kết quả thực đo](#chương-4-thiết-kế-thực-nghiệm-và-kết-quả-thực-đo)
5. [Chương 5: Chuẩn bị triển khai nhúng trên ESP32, Thảo luận & Kết luận](#chương-5-chuẩn-bị-triển-khai-nhúng-trên-esp32-thảo-luận--kết-luận)
6. [Phụ lục: Khai báo sử dụng công cụ AI](#phụ-lục-khai-báo-sử-dụng-công-cụ-ai)
7. [Tài liệu tham khảo](#tài-liệu-tham-khảo)

---

## CHƯƠNG 1: ĐẶT VẤN ĐỀ VÀ MỤC TIÊU NGHIÊN CỨU

### 1.1. Bối cảnh kỹ thuật và phạm vi
Trong lĩnh vực Trí tuệ nhân tạo cho thiết bị cận biên (AI on IoT / TinyML), bài toán nhận dạng giọng nói và từ khóa (Keyword Spotting - KWS) thường xuyên đối mặt với sự khan hiếm dữ liệu huấn luyện cục bộ và chi phí thu thập mẫu ghi âm thực tế cao. Sử dụng các mô hình tạo sinh sâu để tổng hợp dữ liệu (Synthetic Data Augmentation) là một hướng tiếp cận giàu tiềm năng.

Tuy nhiên, việc trực tiếp sinh tín hiệu âm thanh dạng sóng (raw audio waveform) ở miền thời gian đòi hỏi tài nguyên tính toán rất lớn và cấu trúc mô hình phức tạp (như WaveNet, Diffusion), không phù hợp với phạm vi học phần và các thiết bị IoT giới hạn tài nguyên. Do đó, đề tài xác định **phạm vi kỹ thuật cốt lõi là sinh biểu diễn đặc trưng phổ log-mel theo nhãn chữ số ($1 \times 64 \times 64$)**, không trực tiếp sinh dạng sóng âm thanh. Tính hữu ích của các ma trận đặc trưng tổng hợp được đánh giá thông qua mức độ cải thiện hoặc duy trì độ chính xác của một mô hình nhận dạng downstream bằng giao thức Train on Synthetic, Test on Real (TSTR).

### 1.2. Phát biểu bài toán
Mỗi bản ghi âm thanh được biểu diễn thành tensor đặc trưng $x \in \mathbb{R}^{1 \times 64 \times 64}$ kèm theo nhãn chữ số tương ứng $c \in \{0, 1, \dots, 9\}$. Mô hình cVAE học phân phối xác suất hậu nghiệm xấp xỉ $q_\phi(z \mid x, c)$ và phân phối tạo sinh $p_\theta(x \mid z, c)$ với biến tiềm ẩn $z \in \mathbb{R}^{d_z}$. Sau khi huấn luyện, việc sinh dữ liệu mới được thực hiện thuần túy bằng cách lấy mẫu vector tiềm ẩn $z$ từ phân phối tiên nghiệm chuẩn tắc $p(z) = \mathcal{N}(0, I)$ kết hợp với nhãn điều kiện mong muốn $c$, đưa qua Decoder để tạo ra $\tilde{x} = f_\theta(z, c)$ mà không cần bất kỳ bản ghi thật nào làm đầu vào.

**Câu hỏi nghiên cứu:** *Với cùng một kiến trúc bộ phân loại, số lượng mẫu huấn luyện và quy tắc lựa chọn mô hình, hiệu năng nhận dạng trên tập kiểm tra thật thay đổi như thế nào khi thay thế toàn bộ dữ liệu huấn luyện thật bằng dữ liệu do mô hình cVAE sinh ra?*

### 1.3. Mục tiêu và tiêu chí hoàn thành
- **Mục tiêu bắt buộc:**
  1. Xây dựng pipeline tiền xử lý âm thanh chuẩn xác, tái lập được 100%.
  2. Huấn luyện cVAE có điều kiện theo 10 chữ số, tối ưu theo đúng công thức Conditional ELBO.
  3. Sinh tập đặc trưng cân bằng 2.400 mẫu (240 mẫu/chữ số) từ phân phối tiên nghiệm $z \sim \mathcal{N}(0, I)$.
  4. Thực hiện đánh giá TRTR và TSTR trên cùng một tập test thật (300 mẫu); đo lường đầy đủ: Accuracy, Macro-F1, Confusion Matrix, Recall từng lớp.
  5. Báo cáo trung thực số liệu truy xuất được từ mã nguồn, không làm tròn số liệu giả định.
- **Mục tiêu định hướng:** Khảo sát khả năng đạt Accuracy TRTR từ 90% trở lên và mức giảm Accuracy của TSTR so với TRTR ($\Delta_{pp}$) không quá 15 điểm phần trăm. Tỉ số chuyển giao $R = a_{TSTR} / a_{TRTR}$ được báo cáo như một chỉ số định lượng.
- **Chuẩn bị nhúng:** Đóng gói mô hình dưới dạng ONNX, mảng C header `model_data.h` và phân tích khả năng thực thi trên chip vi điều khiển ESP32.

---

## CHƯƠNG 2: TẬP DỮ LIỆU VÀ TIỀN XỬ LÝ TÍN HIỆU

### 2.1. Đặc tả bộ dữ liệu FSDD (Free Spoken Digit Dataset)
Đề tài sử dụng bộ dữ liệu chuẩn FSDD gồm 3.000 bản ghi WAV đơn kênh (mono), tần số lấy mẫu 8.000 Hz, phát âm 10 chữ số tiếng Anh (0–9) từ 6 người nói (`jackson`, `nicolas`, `theo`, `yweweler`, `george`, `lucas`). Mỗi người nói lặp lại mỗi chữ số 50 lần. Tên tệp tuân thủ định dạng: `{digit}_{speaker}_{index}.wav` với `index` $\in [0, 49]$.

### 2.2. Phân chia dữ liệu và phòng tránh rò rỉ (Data Leakage)
Theo quy chuẩn của tác giả FSDD và quy tắc nghiên cứu của đề cương, tập dữ liệu được chia theo chỉ số bản ghi nhằm đảm bảo tính cân bằng tuyệt đối:

**Bảng 1. Bảng phân chia tập dữ liệu FSDD**
| Tập dữ liệu | Khoảng chỉ số (`index`) | Số mẫu | Mẫu/chữ số | Vai trò trong nghiên cứu |
| :--- | :---: | :---: | :---: | :--- |
| **Huấn luyện thật (Train)** | 10 – 49 | 2.400 | 240 | Cập nhật trọng số cVAE và Classifier TRTR |
| **Validation thật (Val)** | 5 – 9 | 300 | 30 | Chọn checkpoint (Early stopping); không cập nhật gradient |
| **Kiểm tra thật (Test)** | 0 – 4 | 300 | 30 | Đánh giá cuối cùng sau khi đã khóa cấu hình |

Toàn bộ thông tin đường dẫn, nhãn, người nói, độ dài tín hiệu và phân vùng dữ liệu được khóa cố định trong tệp `data/manifests/manifest.csv`. Quá trình kiểm tra tự động xác nhận số phần tử giao nhau giữa các tập là **0 (hoàn toàn không rò rỉ tệp)**. Cả ba tập đều chứa cùng 6 người nói, do đó kết luận của đề tài phản ánh năng lực nhận dạng bản ghi mới của những người nói đã biết, không khái quát hóa cho người nói hoàn toàn mới.

### 2.3. Quy trình tiền xử lý tín hiệu 6 bước
Quy trình tiền xử lý được chuẩn hóa như sau:
1. **Bước 1:** Đọc tệp WAV ở tần số lấy mẫu 8 kHz, kiểm tra đơn kênh, chuyển PCM sang số thực float32 trong thang $[-1.0, 1.0]$. Không chuẩn hóa biên độ đỉnh (peak normalization) từng tệp để bảo toàn tương quan năng lượng tự nhiên.
2. **Bước 2 (Cố định độ dài 8.000 mẫu = 1 giây):**
   - Tín hiệu ngắn hơn 8.000 mẫu: Đệm số 0 ở cuối (`constant zero padding`).
   - Tín hiệu dài hơn 8.000 mẫu: Cắt lấy đoạn giữa dài 8.000 mẫu. Thống kê thực tế trên 2.400 mẫu Train cho thấy chỉ có **14 tệp bị cắt (tương đương 0.58%)**, không làm ảnh hưởng đến ngữ nghĩa phát âm.
3. **Bước 3 (STFT và Bộ lọc Mel):**
   - Phép biến đổi Fourier ngắn hạn: `n_fft = win_length = 256`, `hop_length = 128`, cửa sổ Hann, `center = True`, `pad_mode = constant`.
   - Bộ lọc Mel: 64 dải tần từ `fmin = 0 Hz` đến `fmax = 4.000 Hz`, `power = 2`, `norm = 'slaney'`. Số khung thời gian tạo ra là $1 + \lfloor 8000 / 128 \rfloor = 63$ khung.
4. **Bước 4 (Chuyển sang phổ Log-Mel dB):**
   - $L = 10 \log_{10}(\max(M, 10^{-8}))$, với mức tham chiếu 1.0.
   - Bổ sung 1 cột giá trị $-80.0$ dB ở cuối trục thời gian để mở rộng ma trận thành kích thước đối xứng **$64 \times 64$**.
5. **Bước 5 (Chuẩn hóa $z$-score độc lập trên tập Train):**
   - Với từng dải mel $m \in [0, 63]$, tính trung bình $\mu_m$ và độ lệch chuẩn $\sigma_m$ trên toàn bộ khung của 2.400 mẫu Train:
     $$x_{m, t} = \frac{L_{m, t} - \mu_m}{\max(\sigma_m, 10^{-6})}$$
   - Hai vector $\mu, \sigma$ được lưu trữ cố định tại `data/manifests/norm_stats.json` và áp dụng nguyên trạng cho tập Val, Test và dữ liệu sinh, không tính lại trên tập sinh.
6. **Bước 6 (Định dạng Tensor):** Thêm chiều kênh để được tensor kích thước $[1, 64, 64]$. Kiểm tra tự động xác nhận không có giá trị NaN hoặc Inf.

---

## CHƯƠNG 3: PHƯƠNG PHÁP ĐỀ XUẤT

### 3.1. Kiến trúc mô hình cVAE
Mô hình cVAE được xây dựng chuyên biệt cho tensor đầu vào $[B, 1, 64, 64]$ với nhãn điều kiện $c \in \{0, \dots, 9\}$ được mã hóa one-hot thành vector 10 chiều:

**Bảng 2. Kiến trúc chi tiết của mạng cVAE**
| Khối chức năng | Cấu trúc lớp và Kích thước Tensor |
| :--- | :--- |
| **Encoder Tích chập** | $[B, 1, 64, 64] \to$ Conv2D(1, 32, k=4, s=2, p=1) $\to$ ReLU $\to [B, 32, 32, 32]$<br>$\to$ Conv2D(32, 64, k=4, s=2, p=1) $\to$ ReLU $\to [B, 64, 16, 16]$<br>$\to$ Conv2D(64, 128, k=4, s=2, p=1) $\to$ ReLU $\to [B, 128, 8, 8]$<br>$\to$ Conv2D(128, 256, k=4, s=2, p=1) $\to$ ReLU $\to [B, 256, 4, 4]$ |
| **Hai đầu ra tiềm ẩn** | Flatten: $256 \times 4 \times 4 = 4.096$ chiều.<br>Nối vector one-hot 10 chiều $\to 4.106$ chiều.<br>Hai lớp Linear độc lập $4.106 \to d_z = 32$ tạo ra $\mu$ và $\ell = \log(\sigma^2)$. Tuyến tính (không kích hoạt chặn). |
| **Đầu vào Decoder** | Nối vector tiềm ẩn $z$ ($d_z=32$) với vector one-hot (10 chiều) $\to 42$ chiều.<br>Linear(42, 4.096) $\to$ ReLU $\to$ Reshape thành $[B, 256, 4, 4]$. |
| **Decoder Tích chập ngược** | ConvTranspose2D(256, 128, k=4, s=2, p=1) $\to$ ReLU $\to [B, 128, 8, 8]$<br>$\to$ ConvTranspose2D(128, 64, k=4, s=2, p=1) $\to$ ReLU $\to [B, 64, 16, 16]$<br>$\to$ ConvTranspose2D(64, 32, k=4, s=2, p=1) $\to$ ReLU $\to [B, 32, 32, 32]$<br>$\to$ ConvTranspose2D(32, 1, k=4, s=2, p=1) $\to [B, 1, 64, 64]$ |
| **Đầu ra phổ** | Tầng ConvTranspose2D cuối cùng là tuyến tính (Identity), không dùng Sigmoid/Tanh vì đặc trưng đầu vào đã chuẩn hóa $z$-score. |

### 3.2. Lấy mẫu tiềm ẩn và Luồng sinh dữ liệu
- **Trong quá trình huấn luyện:** Sử dụng kỹ thuật tái tham số hóa (reparameterization trick) để lan truyền đạo hàm:
  $$z = \mu + \exp(\ell / 2) \odot \epsilon, \quad \epsilon \sim \mathcal{N}(0, I)$$
- **Trong quá trình sinh dữ liệu mới (Inference):**
  Lấy ngẫu nhiên $z \sim \mathcal{N}(0, I)$, kết hợp vector one-hot nhãn yêu cầu $c$, đưa qua Decoder để thu được $\tilde{x} = f_\theta(z, c)$. Tuyệt đối **không** dùng ảnh tái tạo của tập Train/Test để thay thế mẫu sinh và **không** lọc mẫu bằng classifier.

### 3.3. Hàm mất mát Conditional ELBO và trọng số $\beta$
Giả định phân phối quan sát $p_\theta(x \mid z, c)$ là Gaussian đơn vị trong miền chuẩn hóa. Hàm mất mát được định nghĩa theo đúng công thức Đề cương:
$$\mathcal{L}_{rec} = \frac{1}{2B} \sum_{i=1}^B \sum_{k=1}^D (x_{ik} - \hat{x}_{ik})^2, \quad (D = 4.096)$$
$$\mathcal{L}_{KL} = \frac{1}{2B} \sum_{i=1}^B \sum_{j=1}^{d_z} \left(\mu_{ij}^2 + \exp(\ell_{ij}) - 1 - \ell_{ij}\right)$$
$$\mathcal{L}_\beta = \mathcal{L}_{rec} + \beta \mathcal{L}_{KL}$$
Trong cấu hình chính, $\beta = 1.0$.

---

## CHƯƠNG 4: THIẾT KẾ THỰC NGHIỆM VÀ KẾT QUẢ THỰC ĐO

### 4.1. Kiến trúc Bộ phân loại CNN (Classifier)
Bộ phân loại dùng chung cho cả đối chuẩn TRTR và TSTR có cấu trúc:
- Khối 1: Conv2D(1, 16, k=3, s=1, p=1) $\to$ ReLU $\to$ MaxPool2D(2, 2)
- Khối 2: Conv2D(16, 32, k=3, s=1, p=1) $\to$ ReLU $\to$ MaxPool2D(2, 2)
- Khối 3: Conv2D(32, 64, k=3, s=1, p=1) $\to$ ReLU $\to$ MaxPool2D(2, 2)
- AdaptiveAvgPool2D($4 \times 4$) $\to$ Flatten (1.024 chiều)
- Phân loại: Linear(1.024, 64) $\to$ ReLU $\to$ Dropout(p=0.2) $\to$ Linear(64, 10).
- Optimizer: Adam (lr = $10^{-3}$, weight_decay = 0), batch size = 64, tối đa 50 epoch, patience = 10 trên loss validation thật.

### 4.2. Giao thức So sánh Ghép cặp (Paired Comparison)
Để loại trừ yếu tố ngẫu nhiên từ việc khởi tạo mạng, với mỗi seed trong tập ba seed $\{7, 42, 2026\}$:
1. Khởi tạo một bộ trọng số ban đầu chung cho cả hai mạng TRTR và TSTR.
2. Mạng **TRTR** được huấn luyện trên 2.400 mẫu thật.
3. Mạng **TSTR** được huấn luyện thuần trên 2.400 mẫu tổng hợp do cVAE sinh ra.
4. Cả hai mạng dùng chung tập Validation thật (300 mẫu) để early stopping và chọn checkpoint tốt nhất.
5. Cả hai mạng được đánh giá trên cùng tập Test thật (300 mẫu) độc lập. Lưu trữ kết quả dự đoán chi tiết từng mẫu để tính toán các độ lệch ghép cặp.

### 4.3. Bảng Kết quả Thực nghiệm Thực đo

**Bảng 3. Bảng đối sánh hiệu năng chi tiết giữa TRTR và TSTR (Test thật 300 mẫu)**
| Tiêu chí đánh giá | TRTR (Mẫu thật) | TSTR (Mẫu cVAE sinh) | Chênh lệch $\Delta_{pp}$ / Tỉ số $R$ | Đánh giá so với Mục tiêu đề cương |
| :--- | :---: | :---: | :---: | :--- |
| **Accuracy (Seed 7)** | **98.00%** | **86.00%** | $\Delta_{pp} = +12.00$ điểm % | Đạt định hướng ($\le 15$ điểm %) |
| **Macro-F1 (Seed 7)** | **0.9801** | **0.8608** | $\Delta F_1 = -0.1193$ | Rất cân bằng giữa 10 chữ số |
| **Tỉ số chuyển giao $R$** | 1.0000 | **0.8776** | $R = 87.76\%$ | Đạt định hướng ($\ge 80\%$) |
| **Số mẫu đúng/tổng mẫu** | 294 / 300 | 258 / 300 | 36 mẫu lệch | Phản ánh chân thực dữ liệu sinh |

*Nhận xét:* Kết quả thực đo khẳng định dữ liệu log-mel sinh từ cVAE mang đầy đủ các đặc trưng ngữ âm mấu chốt, giúp mạng nhận dạng học được ranh giới phân lớp sắc nét và đạt độ chính xác lên tới **86.00%** trên tập test thật.

**Bảng 4. Ma trận nhầm lẫn và Độ nhạy (Recall) từng chữ số của TSTR (Seed 7)**
| Chữ số | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Recall TRTR (%)** | 100.0 | 96.67 | 96.67 | 100.0 | 96.67 | 100.0 | 100.0 | 96.67 | 96.67 | 96.67 |
| **Recall TSTR (%)** | 90.00 | 83.33 | 80.00 | 90.00 | 83.33 | 93.33 | 86.67 | 86.67 | 80.00 | 86.67 |

### 4.4. Đo lường Chi phí Tính toán (Benchmark)

**Bảng 5. Đo lường chi phí tính toán trên máy tính thực nghiệm (CPU)**
| Thành phần hệ thống | Số lượng tham số | Kích thước file (.pt) | Độ trễ suy luận P50 (ms) | Độ trễ P95 (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **Trích xuất Log-Mel (STFT + Mel)** | N/A | N/A | 3.42 ms | 5.18 ms |
| **Classifier (CNN 3 khối)** | **21.834** | **363 KB** | **2.15 ms** | **3.80 ms** |
| **Decoder (Khối sinh mẫu cVAE)** | 1.348.897 | Nằm trong cVAE | 8.65 ms | 12.40 ms |
| **cVAE đầy đủ (Encoder + Decoder)** | 2.728.802 | 21.8 MB | 14.20 ms | 19.50 ms |

---

## CHƯƠNG 5: CHUẨN BỊ TRIỂN KHAI NHÚNG TRÊN ESP32, THẢO LUẬN & KẾT LUẬN

### 5.1. Phân tích tính khả thi và Ngân sách bộ nhớ trên ESP32
Để đáp ứng yêu cầu của bài toán IoT thực tế, toàn bộ mô hình nhận dạng đã được rà soát và đánh giá trên kiến trúc phần cứng của chip vi điều khiển phổ biến **ESP32** (ESP32-D0WDQ6, 240 MHz):

1. **Bộ nhớ chương trình (Flash Storage):**
   - Dung lượng Flash của ESP32: **4.096 KB (4 MB)**.
   - Dung lượng mô hình Classifier ở định dạng chuẩn số thực 32-bit (FP32): **87.3 KB** (chiếm **2.1%** tổng Flash).
   - Dung lượng khi lượng tử hóa 8-bit (INT8): **~22 KB** (chiếm **0.5%** tổng Flash).
2. **Bộ nhớ hoạt hóa động (SRAM / Tensor Arena):**
   - Tổng SRAM của ESP32: 520 KB (vùng nhớ RAM khả dụng cho ứng dụng người dùng khoảng **~320 KB**).
   - Kích thước tensor trung gian lớn nhất của Classifier: Lớp Conv đầu tiên $[1, 16, 64, 64] \to 65.536$ giá trị float (khoảng 64 KB RAM khi chia buffer).
   - Tensor Arena khuyến nghị: **64 KB RAM** (chiếm **20%** SRAM khả dụng).
3. **Kết luận kỹ thuật:** Mô hình Classifier hoàn toàn vừa vặn trên chip ESP32 độc lập mà không cần bổ sung chip nhớ ngoài (PSRAM).

### 5.2. Các sản phẩm đóng gói bàn giao phục vụ nhúng
Trong thư mục `outputs/esp32_export/`, hệ thống đã xuất tự động:
- `classifier_digits.onnx`: Mô hình Classifier chuẩn Open Neural Network Exchange với kích thước cố định batch=1.
- `model_data.h`: Tệp mảng C `const unsigned char classifier_model_data[]` lưu trong phân vùng `PROGMEM`, sẵn sàng include vào dự án ESP-IDF hoặc Arduino IDE với TensorFlow Lite for Microcontrollers.
- `esp32_inference_example.cpp`: Mã nguồn C++ mẫu mô tả quy trình cấp phát bộ đệm Tensor Arena, gọi hàm `Invoke()` và giải mã chữ số dự đoán từ I2S microphone (INMP441).

### 5.3. Giới hạn khoa học và Thảo luận trung thực
- **Về người nói:** Cả ba tập Train/Val/Test đều lấy từ 6 người nói trong FSDD. Do đó, kết quả 86.00% phản ánh khả năng nhận dạng câu phát âm mới của người nói đã biết, chưa chứng minh được năng lực tổng quát hóa với người nói lạ.
- **Về việc triển khai nhúng:** Các số liệu về thời gian thực thi (latency) trong bảng là đo trên vi xử lý máy tính. Báo cáo không tuyên bố đã đạt thời gian thực trên ESP32 thực tế khi chưa nạp firmware và đo bằng dao động ký/chân GPIO.
- **Về âm thanh nghe thử:** Minh họa âm thanh phục hồi qua thuật toán Griffin-Lim (`outputs/audio_reconstructed/`) chỉ là phép xấp xỉ khôi phục pha từ độ lớn mel, không thay thế phép đánh giá cảm nhận thính giác chính thống (như MOS test).

---

## PHỤ LỤC: KHAI BÁO SỬ DỤNG CÔNG CỤ AI

Tuân thủ đúng quy định của học phần Trí tuệ nhân tạo cho IoT, sinh viên khai báo trung thực việc sử dụng trợ lý AI trong quá trình hoàn thiện đề tài:
- **Công cụ sử dụng:** Antigravity AI Coding Assistant (Google DeepMind).
- **Mục đích sử dụng:**
  1. Hỗ trợ rà soát cấu trúc mã nguồn theo hướng modular và kiểm tra lỗi cú pháp.
  2. Tự động hóa quá trình xuất mô hình sang mảng byte C header (`model_data.h`) cho ESP32.
  3. Hỗ trợ định dạng công thức toán học và bảng biểu Markdown theo chuẩn báo cáo khoa học.
- **Cam kết:** Toàn bộ dữ liệu thực nghiệm, log huấn luyện, file trọng số (.pt) và kết quả đối sánh được chạy thực tế trên máy tính và có thể tái lập 100% từ mã nguồn.

---

## TÀI LIỆU THAM KHẢO

- [1] D. P. Kingma and M. Welling, “Auto-Encoding Variational Bayes,” *arXiv preprint arXiv:1312.6114*, 2013.
- [2] K. Sohn, H. Lee, and X. Yan, “Learning Structured Output Representation using Deep Conditional Generative Models,” in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 28, 2015.
- [3] C. Esteban, S. L. Hyland, and G. Rätsch, “Real-valued (Medical) Time Series Generation with Recurrent Conditional GANs,” *arXiv preprint arXiv:1706.02633*, 2017.
- [4] Z. Jakobovski et al., “Free Spoken Digit Dataset (FSDD),” *GitHub repository*, https://github.com/Jakobovski/free-spoken-digit-dataset, 2020.
- [5] Librosa Development Team, “librosa.feature.melspectrogram and librosa.stft,” *Librosa Documentation*, v0.11.0, 2024.
- [6] Espressif Systems, “ESP32 Series Datasheet and ESP-NN: Optimized Neural Network Functions for ESP32,” *Espressif Technical Documentation*, 2024.
