# Bước 5 · Failure case, limitation, cải tiến

Cấu hình chạy: 12 ảnh đường thật (`data/images/train1..12.png`, 256×96 px, giữ nguyên độ phân giải), seed 0.
Kết quả: `results/summary.csv`, `results/flags.csv`, `results/trend.png`; đối chiếu số bằng `python tools/check_numbers.py`.
**Nguồn ảnh:** `____` (nhóm điền tên dataset/nguồn, giấy phép và cách lấy 12 ảnh này).

## Failure case chọn phân tích: nhiễu cảm biến làm luật "độ nét" coi ảnh xấu là ảnh nét hơn
- **Điều kiện:** cùng 12 ảnh, thêm nhiễu Gaussian với σ = 5, 10, 20, 40 mức xám.
- **Nhóm quan sát được (tự đo):**
  - blur_score trung bình: baseline 717,7; σ=5: 942,8 (1,3 lần); σ=10: 1607 (2,2 lần); σ=20: 4127 (5,7 lần); σ=40: 12553 (17,5 lần).
  - Số keypoint ORB tăng từ 196 (baseline) lên 260 ở σ=10 và 426 ở σ=20 (+117%).
  - Luật cờ (blur / tối / chói) gắn cờ **0%** frame ở cả 4 mức noise và cả 4 mức rain; baseline cũng 0% cờ. Vệt mưa 2400/frame (chuẩn 640×360) cũng làm blur_score tăng (1279, khoảng 1,8 lần).
- **Ý nghĩa trong phạm vi số đo:** với metric blur_score hiện tại, ảnh nhiễu hoặc có vệt mưa trông "nét hơn" ảnh gốc, nên luật cờ không phát hiện được hai loại lỗi này.
- **Suy luận kỹ thuật (nhóm CHƯA đo):** thuật toán dựa trên feature (visual odometry, SLAM) có thể nhận keypoint do nhiễu thay vì cấu trúc cảnh; detector có thể giảm độ tin cậy. Đây là giả thuyết, cần chạy detector hoặc pipeline thật mới kết luận được.
- **Paper/repo cho biết:** theo abstract, camera-only model rất dễ tổn thương trước corruption ảnh (Dong và cộng sự, CVPR 2023). Đây là kết luận trên dataset và model của paper, **không** so trực tiếp được với các con số ở trên.

## Quan sát phụ (tự đo, cùng bảng)
- Luật blur không phân biệt "nhoè" với "thiếu sáng": night ×0,6 làm blur_score giảm từ 717,7 xuống 259,9 và bị cờ blur 83%, trong khi cờ "tối" chưa bật (mean_gray ≈ 38,3 > ngưỡng 32,6). Từ ×0,35 trở đi cờ tối bật 100%.
- Glare: +60 không bị cờ nào; +120 bị cờ chói 42%; +180 là 83%; +255 là 100%.
- Blur Gaussian σ=1 (chuẩn 640 px) chỉ bị cờ 8%; từ σ=2 là 100%.

## Limitation của benchmark lớp học
- Ảnh rất nhỏ (256×96) và nguồn/giấy phép cần ghi rõ; chỉ 12 ảnh, không có ground truth, **không chạy detector** → không kết luận được mAP hay độ chính xác.
- Tham số blur và rain được co theo độ phân giải so với chuẩn 640 px rộng (σ thực áp dụng = σ×0,4; số vệt mưa theo diện tích). Đây là lựa chọn của nhóm, không phải chuẩn của nguồn nào.
- Lỗi là mô phỏng đơn giản: blur Gaussian đều (không phải nhoè do chuyển động), night chỉ nhân độ sáng (không thêm nhiễu), nhiễu Gaussian thêm sau 8-bit (không qua ISP của camera thật), mưa là vệt thẳng. Mức noise σ = 20, 40 rất nặng so với camera thật; σ = 5, 10 thực tế hơn.
- Ngưỡng cờ hiệu chuẩn trên chính baseline (in-sample): blur_score < 350,8 và mean_gray < 32,6. Baseline vốn khá tối (mean_gray ≈ 64) nên ngưỡng tối khá thấp; đổi cảnh thì ngưỡng cần hiệu chuẩn lại.
- orb_kp là proxy cho thuật toán dựa trên feature và phụ thuộc kích thước ảnh nhỏ.
- Latency mới đo trên CPU laptop (`results/latency.csv`), chưa đo trên phần cứng xe. **Giả thuyết** nguyên nhân: Laplacian khuếch đại nhiễu tần số cao nên không tách được "chi tiết thật" khỏi "nhiễu".

## Đề xuất cải tiến / fallback (nối với failure ở trên)
1. Thêm **ước lượng nhiễu** làm metric thứ hai; luật cờ: blur_score thấp **hoặc** nhiễu cao → giảm trọng số camera.
2. Chuẩn hoá blur_score theo độ sáng trước khi so ngưỡng, để không nhầm "tối" với "nhoè".
3. Fallback: khi cờ bật, giảm trọng số camera trong fusion hoặc dựa vào LiDAR/radar (đề xuất thiết kế, chưa kiểm chứng).

## Kết quả cải tiến: bảng cờ trước/sau (tự đo, vai C)
**Kỳ vọng ban đầu:** chạy lại `run_benchmark.py` với luật mới; tỷ lệ cờ ở noise σ ≥ 10 và rain ≥ 1200 vệt tăng khỏi 0%, trong khi tỷ lệ cờ ở baseline vẫn ≈ 0%.
**Kết quả: ĐẠT trên 6 ảnh test.** Riêng rain 200 và 600 vệt vẫn chưa được phát hiện.

**Đã thêm vào code** (`src/metrics.py`, `src/run_benchmark.py`):
- **Ước lượng nhiễu** `noise_sigma` (Immerkær 1996), đơn vị mức xám. Cờ nhiễu bật khi noise_sigma > 2 × median baseline.
- **Chuẩn hoá blur theo độ sáng** `blur_norm = blur_score / mean_gray²`. Cờ blur dùng blur_norm < 0,5 × median baseline, thay cho blur_score.
- Thêm vệt mưa `streak_ratio` (white top-hat 5×1 px). Cờ mưa bật khi streak_ratio > 2 × median baseline **và** không có cờ nhiễu.
- Cờ tối và cờ chói giữ nguyên.
- Hệ số 0,5 và 2 được chọn **trước khi chạy**.
- Để tránh hiệu chuẩn in-sample, ngưỡng được đặt trên baseline của 6 ảnh đầu (train1, 10, 11, 12, 2, 3). Tỷ lệ cờ báo cáo trên 6 ảnh còn lại (train4…9).

Bảng dưới là tỷ lệ frame bị gắn cờ bất kỳ (`flag_any`), cả hai luật tính trên **cùng 6 ảnh test**. Nguồn: `results/flags_compare.csv`. Mỗi ảnh = 17 điểm phần trăm.

| Điều kiện | Mức | Luật cũ | Luật mới | Cờ mới nào bật |
|---|---|---|---|---|
| **baseline** | – | **0%** | **0%** | – |
| **noise** | σ = 5 | 0% | **100%** | nhiễu |
| | σ = 10 | 0% | **100%** | nhiễu |
| | σ = 20 | 0% | **100%** | nhiễu |
| | σ = 40 | 0% | **100%** | nhiễu |
| **rain** | 200 vệt | 0% | 0% | – |
| | 600 vệt | 0% | 0% | – |
| | 1200 vệt | 0% | **100%** | mưa |
| | 2400 vệt | 0% | **100%** | mưa |
| blur | σ = 1 | 17% | 0% | – |
| | σ = 2 / 4 / 8 | 100% | 100% | blur |
| night | ×0,6 | 100% (cờ blur, **sai nguyên nhân**) | 0% | – |
| | ×0,35 / 0,2 / 0,1 | 100% (blur + tối) | 100% | tối (đúng nguyên nhân) |
| glare | +60 | 0% | **100%** | blur (**tác dụng phụ**) |
| | +120 / 180 / 255 | 67% / 83% / 100% | 100% | blur + chói |

**Nhóm quan sát được (tự đo):**
- **Noise:** noise_sigma trung bình 4,2 / 7,2 / 13,4 / 24,6 ở σ = 5 / 10 / 20 / 40. Ngưỡng là 3,90 (baseline ≈ 1,96). Riêng σ = 5 chỉ vượt ngưỡng sát.
- **Rain:** trên 6 ảnh test, streak_ratio lớn nhất ở 200 / 600 vệt là 0,065 / 0,093, dưới ngưỡng 0,104. Ở 1200 / 2400 vệt, giá trị nhỏ nhất là 0,109 / 0,171, vượt ngưỡng. Baseline ảnh thật đã có streak_ratio 0,029-0,077, cao hơn khoảng 10 lần cảnh tổng hợp.
- **Glare +60:** blur_score gần như không đổi (−0,4%), nhưng mean_gray tăng từ 64 lên 95, nên blur_norm giảm 55% và cờ blur bật. Chuẩn hoá theo mean² đã sửa quá tay: hết nhầm "tối" thành "nhoè" thì lại nhầm "sáng" thành "nhoè".
- **Night ×0,6:** không còn bị cờ nào (mean_gray 38,3 > ngưỡng tối 33,3), dù orb_kp đã giảm 61%.

**Suy luận kỹ thuật (nhóm CHƯA đo):**
- Mưa nhẹ bị lẫn với cột, mép xe, vạch kẻ: đây cũng là nét sáng mảnh thẳng đứng có sẵn trong cảnh.
- Glare là ánh sáng cộng thêm (offset), không phải nhân (gain) như night, nên chuẩn hoá theo mean² chỉ đúng với lỗi kiểu nhân.

## Engineering decision và trade-off (vai C)
- **Quyết định:** dùng luật mới thay luật cũ để quyết định giảm trọng số camera.
  - Lý do: luật cũ bỏ sót hoàn toàn hai loại lỗi (noise, rain: 0%), còn luật mới bắt được noise ở mọi mức và rain từ 1200 vệt, mà không tăng cờ giả ở baseline (0%).
  - Glare +120 trở lên vốn đã bị cờ chói, nên tác dụng phụ của blur_norm chỉ làm đổi quyết định ở glare +60.
- **Chi phí:** luật mới tốn khoảng 0,4 ms/frame ở 256×96 (`results/latency.csv`, CPU Intel, Python), không đáng kể so với ngân sách 33 ms của camera 30 fps. Chưa đo trên phần cứng nhúng của xe.
- **Trade-off 1, độ nhạy và cờ giả:** hạ ngưỡng streak_ratio để bắt mưa 200-600 vệt sẽ tiến sát baseline (tới 0,077), nên ảnh không mưa có nhiều cột/vạch dễ bị cờ giả. Ngưỡng nhiễu hiện chỉ vừa đủ bắt σ = 5. Giả thuyết, chưa đo: ảnh đêm ISO cao có nhiễu nền lớn hơn, có thể bị giảm trọng số oan.
- **Trade-off 2, phát hiện và đúng nguyên nhân:** blur_norm báo đúng nguyên nhân cho ảnh tối nhưng báo sai cho glare. Đổi lại, night ×0,6 và blur σ = 1 không còn bị cờ nào. Nếu chỉ cần quyết định "giảm trọng số" thì chấp nhận được. Nếu cần báo nguyên nhân cho người vận hành thì phải sửa tiếp.
- **Hướng sửa tiếp (chưa làm):**
  - chuẩn hoá blur theo độ tương phản (blur_score / var(ảnh xám)) thay vì mean², để không bị ảnh hưởng bởi offset của glare;
  - dùng hướng của vệt để tách mưa khỏi cột/vạch;
  - tăng số ảnh test;
  - chạy detector để kiểm chứng proxy.

Lưu ý: từ vòng này, `results/flags.csv` là luật mới (chỉ 6 ảnh test). Số của luật cũ ở các mục trên nằm trong `results/flags_old.csv`. Chi tiết thêm (latency từng metric, ngưỡng) ở `notes/improvement.md`.
