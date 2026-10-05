# Báo cáo cá nhân · Sensor Reality Sprint T1: Sức khoẻ camera ADAS

| | |
|---|---|
| Họ tên | Nguyễn Văn Bảo |
| MSSV | 2A202602862 |
| Vai trong nhóm | C · Metric & cải tiến |
| Phụ trách pitch | Method + Engineering decision |
| Nhánh / commit | `Bao` · `9e80885` (code + kết quả), `44b6d9e` (bảng trước/sau trong `failure_case.md`) |

Quy ước trong báo cáo:
- **(tự đo)**: số nhóm chạy ra, có trong `results/`.
- **(nguồn)**: điều paper nói.
- **(giả thuyết)**: suy luận chưa kiểm chứng.

---

## 1. Bài toán
Một xe ADAS dùng camera cùng các cảm biến khác. Khi ảnh camera xấu đi (nhoè, thiếu sáng, chói, nhiễu, mưa), hệ thống cần **tự phát hiện** để **giảm trọng số camera** trong fusion, thay vì tin vào một ảnh hỏng.

Câu hỏi của nhóm:
1. Với từng loại lỗi, các chỉ số chất lượng ảnh thay đổi thế nào?
2. Một luật cờ đơn giản dựa trên các chỉ số đó có phát hiện được ảnh xấu không, mà không gắn cờ nhầm ảnh tốt?

**Claim ban đầu:** tăng mức blur, night hoặc glare thì blur_score và số keypoint ORB giảm; glare thì sat_ratio tăng. Giả thuyết cần kiểm tra: noise và rain có làm blur_score giảm như blur không?

## 2. Nguồn
- Dong và cộng sự, *Benchmarking Robustness of 3D Object Detection to Common Corruptions*, CVPR 2023 ([arXiv 2303.11040](https://arxiv.org/abs/2303.11040)).
- **(nguồn, theo abstract):** paper thiết kế 27 loại corruption cho LiDAR và camera, tạo các benchmark KITTI-C, nuScenes-C, Waymo-C, đánh giá 24 mô hình 3D detection. Kết luận: mô hình chỉ dùng camera rất dễ tổn thương trước corruption ảnh.
- **Nhóm tái hiện:** chỉ ý tưởng "tạo corruption có kiểm soát trên cùng dữ liệu rồi đo". Nhóm **không** tái hiện số của paper. Metric của nhóm là **proxy** chất lượng ảnh, không phải mAP. Lý do: paper cần dataset và detector 3D lớn, không chạy được trong 120 phút.
- Phần đọc chi tiết paper (method, metric, limitation) do vai A phụ trách, xem `PLAN.md` Bước 2.

## 3. Thiết kế benchmark
- **Dữ liệu:** 12 ảnh đường thật `data/images/train1..12.png`, 256×96 px, giữ nguyên độ phân giải.
- **Lỗi:** 5 loại × 4 mức (`src/degrade.py`), mọi lỗi tạo từ cùng ảnh gốc, seed cố định.

| Lỗi | 4 mức | Ghi chú |
|---|---|---|
| blur | Gaussian σ = 1, 2, 4, 8 px | định nghĩa ở chuẩn 640 px, co theo ảnh (×0,4) |
| night | độ sáng ×0,6 / 0,35 / 0,2 / 0,1 | chỉ nhân độ sáng, không thêm nhiễu |
| glare | vầng sáng +60 / 120 / 180 / 255 mức xám | |
| noise | Gaussian σ = 5 / 10 / 20 / 40 mức xám | thêm sau 8-bit |
| rain | 200 / 600 / 1200 / 2400 vệt/frame | chuẩn 640×360, co theo diện tích |

- **Metric** (`src/metrics.py`). Ban đầu có 5 metric:
  - blur_score = var(Laplacian ảnh xám);
  - sat_ratio = tỷ lệ pixel ≥ 250;
  - entropy (bit);
  - mean_gray (0-255);
  - orb_kp = số keypoint ORB.

  Phần cải tiến thêm 3 metric, xem mục 5.
- **Luật cờ cũ:**
  - cờ blur: blur_score < 0,5 × median baseline (= 350,8);
  - cờ tối: mean_gray < 0,5 × median baseline (= 32,6);
  - cờ chói: sat_ratio > 0,05.

## 4. Kết quả baseline và failure case (tự đo, luật cũ, 12 ảnh)
| Điều kiện | blur_score | mean_gray | orb_kp | Cờ bất kỳ (luật cũ) |
|---|---|---|---|---|
| baseline | 717,7 | 64,4 | 196 | 0% |
| blur σ = 2 | 91,0 | 64,4 | 87 | 100% |
| night ×0,6 | 259,9 | 38,3 | 76 | 83% (cờ **blur**, không phải cờ tối) |
| glare +255 | 391,6 | 183,6 | 94 | 100% |
| **noise σ = 20** | **4127 (×5,7)** | 64,2 | **426 (+117%)** | **0%** |
| **noise σ = 40** | **12553 (×17,5)** | 66,2 | 655 | **0%** |
| **rain 2400** | **1279 (×1,8)** | 75,6 | 359 | **0%** |

**Failure case:** nhiễu cảm biến và vệt mưa làm blur_score **tăng** chứ không giảm. Ảnh xấu trông "nét hơn" ảnh gốc, nên luật cờ bỏ sót 100% ở cả 4 mức noise và cả 4 mức rain. Claim ban đầu "lỗi làm blur_score giảm" **sai** với noise và rain.

**Quan sát phụ:** cờ blur không phân biệt "nhoè" với "tối". Ở night ×0,6, cờ blur bật còn cờ tối chưa bật.

**Nguyên nhân (giải thích kỹ thuật):**
- Laplacian là bộ lọc thông cao. Nó khuếch đại nhiễu và cạnh sắc của vệt mưa giống như chi tiết thật.
- var(Laplacian) tỷ lệ với bình phương độ sáng: nhân ảnh ×k thì var giảm k² lần. Vì vậy ảnh tối bị tính là "kém nét".

## 5. Phần việc của tôi: kiểm tra metric và cải tiến luật cờ
### 5.1 Ba metric mới (`src/metrics.py`)
| Metric | Công thức | Sửa lỗi nào |
|---|---|---|
| `noise_sigma` | Immerkær (1996): chập ảnh xám với kernel `[[1,-2,1],[-2,4,-2],[1,-2,1]]`, σ = √(π/2)·Σ\|r\| / (6(W−2)(H−2)); đơn vị mức xám | nhiễu bị coi là "nét" |
| `blur_norm` | blur_score / mean_gray² | ảnh tối bị coi là "nhoè" |
| `streak_ratio` | tỷ lệ pixel có white top-hat (kernel ngang 5×1) > 20 mức xám, tức nét sáng mảnh gần thẳng đứng | vệt mưa bị coi là "nét" |

### 5.2 Luật cờ mới (`src/run_benchmark.py`)
- Cờ blur: `blur_norm < 0,5 × median baseline`.
- Cờ nhiễu (mới): `noise_sigma > 2 × median baseline`.
- Cờ mưa (mới): `streak_ratio > 2 × median baseline` **và** không có cờ nhiễu. Nhiễu nặng cũng làm streak_ratio tăng, nên điều kiện này giúp báo đúng nguyên nhân.
- Cờ tối và cờ chói giữ nguyên.

Hai quyết định để kết quả không bị "làm đẹp":
1. **Hệ số 0,5 và 2 được chọn trước khi chạy**, không dò theo kết quả.
2. **Tách calib/test:** ngưỡng hiệu chuẩn trên baseline của 6 ảnh đầu, tỷ lệ cờ báo cáo trên 6 ảnh sau. Luật cũ hiệu chuẩn trên chính ảnh được đánh giá (in-sample).

Ngưỡng thu được: blur_norm < 0,0899; mean_gray < 33,3; noise_sigma > 3,90; streak_ratio > 0,1044.

Ngoài ra:
- Luật cũ vẫn được giữ trong `results/flags_old.csv` để so sánh.
- Thêm đo latency (`results/latency.csv`).
- Sửa lỗi phần trăm thay đổi ra inf khi baseline bằng 0.
- Sửa `tools/check_numbers.py` để vẫn đối chiếu đúng số của luật cũ.

### 5.3 Kết quả trước/sau (tự đo, 6 ảnh test, `results/flags_compare.csv`)
| Điều kiện | Luật cũ | Luật mới | Cờ mới nào bật |
|---|---|---|---|
| **baseline** | **0%** | **0%** | – |
| **noise σ = 5 / 10 / 20 / 40** | 0% | **100%** ở cả 4 mức | nhiễu |
| **rain 200 / 600** | 0% | 0% | – |
| **rain 1200 / 2400** | 0% | **100%** | mưa |
| blur σ = 1 | 17% | 0% | – |
| blur σ = 2 / 4 / 8 | 100% | 100% | blur |
| night ×0,6 | 100% (sai nguyên nhân: cờ blur) | 0% | – |
| night ×0,35 / 0,2 / 0,1 | 100% | 100% | tối (đúng nguyên nhân) |
| glare +60 | 0% | **100%** | blur (**tác dụng phụ**) |
| glare +120 / 180 / 255 | 67 / 83 / 100% | 100% | blur + chói |

Mỗi ảnh test tương ứng 17 điểm phần trăm.

**Kết luận trong phạm vi số đo:**
- **Đạt mục tiêu:** noise (cả 4 mức) và rain ≥ 1200 vệt từ 0% lên 100%, baseline vẫn 0%.
- **Chưa đạt:**
  - rain 200 và 600 vệt vẫn 0%. Ở các mức này, streak_ratio lớn nhất trên ảnh test là 0,065 / 0,093, dưới ngưỡng 0,104.
  - Baseline ảnh thật đã có streak_ratio 0,029-0,077, vì cảnh thật có nhiều nét sáng mảnh thẳng đứng như cột, mép xe, vạch kẻ (giả thuyết).
- **Tác dụng phụ:** glare +60 bị cờ blur. blur_score gần như không đổi (−0,4%), nhưng mean_gray tăng từ 64 lên 95 nên blur_norm giảm 55%. Chia cho mean² đúng với lỗi **nhân** độ sáng (night), nhưng sai với lỗi **cộng** ánh sáng (glare).
- **Bỏ sót mới:** night ×0,6 không còn bị cờ nào, dù orb_kp đã giảm 61%.

## 6. Engineering decision và trade-off
**Quyết định:** dùng luật mới thay luật cũ để quyết định giảm trọng số camera.
- Luật cũ mù hoàn toàn với hai loại lỗi (noise, rain). Luật mới bắt được chúng mà không tăng cờ giả ở baseline.
- Tác dụng phụ glare chỉ làm đổi quyết định ở glare +60, vì glare +120 trở lên vốn đã bị cờ chói.

**Chi phí** (tự đo, `results/latency.csv`, CPU Intel laptop, Python):

| metric | ms/frame (256×96) | metric | ms/frame (256×96) |
|---|---|---|---|
| mean_gray | 0,02 | blur_score | 0,11 |
| sat_ratio | 0,03 | noise_sigma | 0,12 |
| entropy | 0,04 | blur_norm | 0,14 |
| streak_ratio | 0,05 | orb_kp | 0,47 |

Luật mới tốn khoảng 0,4 ms/frame, rất nhỏ so với ngân sách 33 ms của camera 30 fps. Chưa đo trên phần cứng nhúng của xe.

**Trade-off:**
1. **Độ nhạy và cờ giả:** muốn bắt mưa 200-600 vệt thì phải hạ ngưỡng streak_ratio sát mức baseline (tới 0,077). Khi đó ảnh không mưa có nhiều cột/vạch dễ bị cờ giả, và camera bị giảm trọng số oan. Ngưỡng nhiễu hiện chỉ vừa đủ bắt σ = 5 (4,2 so với 3,90). Ảnh đêm ISO cao có nhiễu nền lớn hơn, có thể bị cờ oan (giả thuyết).
2. **Phát hiện và đúng nguyên nhân:** blur_norm báo đúng nguyên nhân cho ảnh tối nhưng sai cho glare. Nếu chỉ cần quyết định "giảm trọng số" thì chấp nhận được. Nếu cần báo nguyên nhân cho người vận hành hoặc ghi log chẩn đoán thì phải sửa tiếp.
3. **Fallback (đề xuất, chưa kiểm chứng):** khi cờ bật, giảm trọng số camera và dựa nhiều hơn vào LiDAR/radar.

## 7. Limitation
- Chỉ 12 ảnh nhỏ 256×96, test trên 6 ảnh. Sai số tỷ lệ cờ lớn, mỗi ảnh = 17 điểm phần trăm. Nguồn/giấy phép ảnh chưa ghi (vai B).
- **Không chạy detector, không có ground truth.** Mọi metric là proxy, không kết luận được mAP hay độ an toàn.
- Lỗi là mô phỏng đơn giản. Riêng streak_ratio được thiết kế khớp với hình dạng vệt mưa do chính `degrade.py` vẽ, nên **chưa chứng minh** gì với mưa thật (giọt trên kính, mưa mờ).
- Metric mới và luật đã được thử trên cảnh tổng hợp trước khi chạy ảnh thật, nhưng các hướng sửa ở mục 8 được đề xuất **sau khi** thấy kết quả test. Nếu làm, phải ghi rõ là vòng thử thứ hai trên cùng tập test.

## 8. Việc chưa làm và lý do
| Việc | Lý do chưa làm | Hướng làm |
|---|---|---|
| Detector confidence | Đề ghi "nếu còn thời gian"; ảnh 256×96 quá nhỏ, cần tải model (YOLO) và thêm thư viện | So số vật thể và confidence trên ảnh gốc với ảnh lỗi; không cần nhãn |
| Sửa tác dụng phụ glare | Lỗi chỉ lộ ra trên tập test; sửa ngay sẽ có nguy cơ dò theo test | Chuẩn hoá theo độ tương phản `blur_score / var(ảnh xám)`: không bị ảnh hưởng bởi ánh sáng cộng thêm, vẫn khử được lỗi nhân độ sáng |
| Phát hiện mưa nhẹ | Cùng lý do; thiết kế dễ bị ảnh hưởng bởi kết quả đã thấy | Dùng hướng vệt (mưa song song cùng góc) để tách khỏi cột/vạch; thử trên ảnh mới |

## 9. Chạy lại
```bash
pip install -r requirements.txt
python src/run_benchmark.py --n 12 --seed 0    # ghi toàn bộ results/
python tools/check_numbers.py                  # đối chiếu số của luật cũ trong failure_case.md
```
Môi trường đã chạy: python 3.11.9, opencv 4.7.0, numpy 1.26.4. Số của luật cũ khớp với lần chạy trước của nhóm (python 3.12.3, opencv 4.13.0).
Chi tiết thêm: `notes/improvement.md`, `notes/failure_case.md`.
