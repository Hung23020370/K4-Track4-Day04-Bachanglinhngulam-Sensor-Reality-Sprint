# Vai C · Metric, cải tiến luật cờ, engineering decision

Cấu hình: 12 ảnh thật `data/images/train*.png` (256×96 px, giữ nguyên độ phân giải), seed 0, chạy bằng `python src/run_benchmark.py --n 12 --seed 0` (python 3.11.9, opencv 4.7.0, numpy 1.26.4).
Các số của 5 metric cũ và luật cũ **trùng khớp** với lần chạy trước (python 3.12.3, opencv 4.13.0). Kiểm tra bằng `python tools/check_numbers.py`.

## 1. Kiểm tra `metrics.py` và luật cờ cũ (tự đo, `results/flags_old.csv`)
| Lỗi của luật cũ | Bằng chứng | Nguyên nhân (giải thích) |
|---|---|---|
| Nhiễu không bị cờ | noise σ = 5…40: cờ 0%, blur_score tăng 1,3 → 17,5 lần | Laplacian khuếch đại nhiễu tần số cao, coi nhiễu là "chi tiết" |
| Mưa không bị cờ | rain 200…2400 vệt: cờ 0%, blur_score tăng tới 1,8 lần | Vệt mưa là cạnh sắc, cũng làm blur_score tăng |
| Tối bị nhầm thành nhoè | night ×0,6: cờ blur 83%, cờ tối 0% | var(Laplacian) tỷ lệ với bình phương độ sáng: nhân ×k thì var giảm k² lần |
| Ngưỡng in-sample | ngưỡng = 0,5 × median của chính 12 ảnh được đánh giá | không có tập kiểm tra riêng |
| `d_sat_ratio_%` có thể = inf | xảy ra khi baseline sat_ratio = 0 (cảnh tổng hợp) | chia cho 0; **đã sửa** thành NaN |

## 2. Cải tiến đã làm (`src/metrics.py`, `src/run_benchmark.py`)
- **`noise_sigma`**: ước lượng σ nhiễu theo Immerkær (1996), *Fast Noise Variance Estimation*, CVIU 64(2). Cách tính: chập ảnh xám với kernel `[[1,-2,1],[-2,4,-2],[1,-2,1]]`, rồi σ = √(π/2)·Σ|r| / (6(W−2)(H−2)). Đơn vị là mức xám.
- **`blur_norm`** = blur_score / mean_gray², không đơn vị. Đây là độ nét đã chuẩn hoá theo độ sáng.
- **`streak_ratio`**: tỷ lệ pixel thuộc nét sáng mảnh gần thẳng đứng. Cách tính: white top-hat với kernel ngang 5×1 px, giữ pixel > 20 mức xám. Đây là proxy cho vệt mưa.
- **Luật mới**:
  - cờ blur: `blur_norm < 0,5 × median baseline`;
  - cờ nhiễu: `noise_sigma > 2 × median baseline`;
  - cờ mưa: `streak_ratio > 2 × median baseline` **và không có cờ nhiễu** (nhiễu σ ≥ 20 cũng làm streak_ratio tăng);
  - cờ tối và cờ chói: giữ như cũ.
- Hệ số 0,5 và 2 được **chọn trước khi chạy**, không dò theo kết quả. Metric và luật đã được thử và chốt trên cảnh tổng hợp trước khi chạy trên ảnh thật.
- **Tách calib/test**: ngưỡng hiệu chuẩn trên baseline của 6 ảnh đầu, báo cáo tỷ lệ cờ trên 6 ảnh sau. Thứ tự là thứ tự tên file sau khi sort: calib = train1, 10, 11, 12, 2, 3; test = train4…9.
- Ngưỡng thu được: blur_norm < 0,0899; mean_gray < 33,3; sat_ratio > 0,05; noise_sigma > 3,90; streak_ratio > 0,1044.

## 3. Kết quả (tự đo, 6 ảnh test, `results/flags_compare.csv`)
| Điều kiện | Cờ bất kỳ, luật cũ | Cờ bất kỳ, luật mới | Ghi chú |
|---|---|---|---|
| baseline | 0% | 0% | không tăng báo động giả (chỉ có 6 ảnh test) |
| noise σ = 5 / 10 / 20 / 40 | 0% | **100%** ở cả 4 mức | noise_sigma trung bình 4,2 / 7,2 / 13,4 / 24,6, ngưỡng 3,90. σ = 5 chỉ vượt ngưỡng sát (baseline ≈ 1,96) |
| rain 200 / 600 vệt | 0% | **0%** | streak_ratio test lớn nhất 0,065 / 0,093, dưới ngưỡng 0,104 |
| rain 1200 / 2400 vệt | 0% | **100%** | streak_ratio test nhỏ nhất 0,109 / 0,171 |
| blur σ = 1 | 17% | 0% | blur nhẹ σ = 1 (thực tế 0,4 px trên ảnh 256 px) không còn bị cờ |
| blur σ = 2…8 | 100% | 100% | giữ nguyên |
| night ×0,6 | 100% (nhưng **sai nguyên nhân**: cờ blur) | **0%** | blur_norm không còn nhầm tối thành nhoè; mean_gray 38,3 vẫn trên ngưỡng tối 33,3 |
| night ×0,35…0,1 | 100% (blur + tối) | 100% (chỉ cờ tối, đúng nguyên nhân) | |
| glare +60 | 0% | **100% (cờ blur)** | **tác dụng phụ lớn nhất**, xem dưới |
| glare +120…255 | 67…100% | 100% | cờ blur bật 100% kèm cờ chói |

**Kết luận trong phạm vi số đo:**
- **Đạt**: kỳ vọng trong `failure_case.md` (noise σ ≥ 10 và rain ≥ 1200 vệt tăng khỏi 0%, baseline ≈ 0%) đạt trên 6 ảnh test.
- **Chưa đạt**: mưa nhẹ (200 và 600 vệt) vẫn 0%. Trên ảnh thật, baseline streak_ratio đã khoảng 0,029-0,077, gấp khoảng 10 lần cảnh tổng hợp (≈ 0,005). Lý do là cảnh thật có sẵn nhiều nét sáng mảnh thẳng đứng (cột, mép xe, vạch). Điều này xác nhận nghi ngờ trước đó: streak_ratio dễ lẫn với cấu trúc thật của cảnh.
- **Tác dụng phụ**: blur_norm làm glare nhẹ (+60) bị cờ blur 100%. Ảnh gốc khá tối (mean_gray ≈ 64); +60 làm mean_gray tăng lên ≈ 95, nên blur_norm giảm khoảng 55% dù blur_score gần như không đổi (−0,4%). Nghĩa là chia cho mean² đã **sửa quá tay**: hết nhầm tối thành nhoè thì lại nhầm sáng thành nhoè. Giả thuyết, chưa đo: lý do là glare là ánh sáng cộng thêm (offset), không phải nhân (gain) như night, nên chuẩn hoá theo mean² chỉ đúng với lỗi kiểu nhân.
- **Đánh đổi**: night ×0,6 và blur σ = 1 không còn bị cờ nào. Ở night ×0,6, orb_kp đã giảm 61%. Luật mới **bỏ sót** những trường hợp mà luật cũ bắt được, dù luật cũ bắt vì sai lý do.

## 4. Engineering decision
**Latency** (tự đo, `results/latency.csv`, ảnh 256×96, CPU Intel, 1 luồng Python, trung bình 20 lần):

| metric | ms/frame | metric | ms/frame |
|---|---|---|---|
| mean_gray | 0,02 | blur_score | 0,11 |
| sat_ratio | 0,03 | noise_sigma | 0,12 |
| entropy | 0,04 | blur_norm | 0,14 |
| streak_ratio | 0,05 | orb_kp | 0,47 |

- Luật mới (blur_norm + noise_sigma + streak_ratio + mean_gray + sat_ratio) tốn khoảng **0,4 ms/frame** ở 256×96. Trên cảnh tổng hợp 640×360 (thử riêng trên máy này) là khoảng 5 ms, vẫn trong ngân sách 33 ms của camera 30 fps. Chưa đo trên phần cứng nhúng của xe.
- **Trade-off ngưỡng**: hạ ngưỡng streak_ratio để bắt mưa nhẹ thì ảnh thật không mưa sẽ dễ bị cờ giả, vì baseline đã cao. Hạ ngưỡng nhiễu (σ = 5 hiện chỉ vượt ngưỡng sát) thì ảnh đêm ISO cao cũng có thể bị giảm trọng số oan (giả thuyết).
- **Vì sao vẫn dùng blur_norm dù có tác dụng phụ**: với quyết định cuối cùng là "giảm trọng số camera", glare +120 trở lên vốn đã bị cờ chói, nên chỉ có glare +60 là đổi kết quả. Còn blur_score thô thì nhầm theo 3 hướng (tối → nhoè, nhiễu → nét, mưa → nét). Nếu cần báo **đúng nguyên nhân** cho người vận hành, nên chuyển cờ blur sang metric khác (xem mục 5).
- **Detector confidence: chưa làm.** Ảnh 256×96 rất nhỏ, không có nhãn, và cần tải model (YOLO) ngoài phạm vi 120 phút. Đây là bước kiểm chứng quan trọng nhất còn thiếu: luật cờ hiện chỉ dựa trên proxy.

## 5. Việc tiếp theo (chưa làm)
1. Sửa tác dụng phụ glare: chuẩn hoá theo độ tương phản (ví dụ blur_score / var(ảnh xám)) thay vì mean², vì nó không bị ảnh hưởng bởi offset sáng. Cần chạy lại để kiểm chứng.
2. Mưa nhẹ: kết hợp streak_ratio với hướng (vệt mưa song song cùng góc) để tách khỏi cột/vạch có sẵn trong cảnh.
3. Tăng số ảnh test. 6 ảnh nên mỗi ảnh = 17 điểm phần trăm, sai số tỷ lệ cờ rất lớn.
