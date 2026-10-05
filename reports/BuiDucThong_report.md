# Báo cáo cá nhân — Failure case và trade-off cho health score camera ADAS

**Họ tên:** Bùi Đức Thông  
**MSSV:** Chưa được cung cấp  
**Nhóm:** Ba chàng lính ngự lâm  
**Vai trò:** C · Metric, failure case và engineering decision  
**Commit cá nhân:** `eee372b60abe36abb592e1859989374145bf5f00` — *Failure case & trade-off* (05/10/2026)

> Quy ước: **[Tự đo]** là số trong các tệp `results/`; **[Nguồn nói]** là nhận định của tài liệu tham khảo; **[Giả thuyết]** là suy luận chưa được xác thực bằng detector hoặc xe thật.

## 1. Bài toán

Hệ thống mô phỏng tính năng giám sát sức khoẻ ảnh camera của xe ADAS. Mục tiêu là phát hiện khi ảnh camera bị suy giảm để hệ thống có thể giảm trọng số của camera trong fusion. Benchmark thử năm loại corruption: Gaussian blur, thiếu sáng, glare, Gaussian noise và vệt mưa.

**[Tự đo]** Bộ benchmark sử dụng 12 ảnh đường `train1..12.png`, độ phân giải 256×96 px, seed 0. Các chỉ số đo là `blur_score`, `sat_ratio`, `entropy`, `mean_gray`, `orb_kp`, `noise_sigma`, `blur_norm` và `streak_ratio`. Chúng là proxy chất lượng ảnh, không phải mAP hay độ chính xác detector.

## 2. Phần việc đã thực hiện trong commit mới nhất

Commit `eee372b` cập nhật toàn bộ `notes/failure_case.md` với ba mục tiêu:

- Gắn nhãn **[Tự đo]**, **[Nguồn nói]** hoặc **[Giả thuyết]** cho từng nhận định để không nhầm số đo của nhóm với kết luận từ paper.
- Đối chiếu các số được trích dẫn với `results/summary.csv`, `results/flags_old.csv`, `results/flags_compare.csv` và `results/latency.csv`.
- Viết lại failure case, giới hạn benchmark và trade-off: khi nào health score phù hợp để hỗ trợ quyết định trong ADAS, và khi nào không nên dùng nó như bằng chứng an toàn độc lập.

## 3. Failure case chính: nhiễu và mưa bị hiểu là ảnh “nét”

| Điều kiện [Tự đo] | `blur_score` trung bình | ORB keypoint | Cờ bất kỳ của luật cũ |
|---|---:|---:|---:|
| Baseline | 717,7 | 196 | 0% |
| Noise σ = 5 | 942,8 | 207 | 0% |
| Noise σ = 10 | 1.607,3 | 260 | 0% |
| Noise σ = 20 | 4.126,8 | 426 | 0% |
| Noise σ = 40 | 12.552,6 | 655 | 0% |
| Rain 2.400 vệt | 1.278,9 | 359 | 0% |

**[Tự đo]** Nhiễu σ = 5–40 làm `blur_score` tăng từ 1,3× đến 17,5× so với baseline; mưa cũng làm chỉ số này tăng. Do luật cũ chỉ xem `blur_score` thấp là nhoè, nó không gắn cờ cho bất cứ mức nhiễu hay mưa nào. Trong phạm vi proxy này, ảnh đã bị corruption lại trông “nét hơn”.

**[Giả thuyết]** Laplacian nhạy với thành phần tần số cao nên không phân biệt được chi tiết thật với nhiễu hoặc vệt mưa. Các keypoint tăng thêm có thể không ổn định cho visual odometry, SLAM hoặc detector; cần chạy các pipeline đó để kiểm chứng.

**[Nguồn nói]** Dong và cộng sự (CVPR 2023) cho thấy mô hình camera-only dễ bị ảnh hưởng bởi corruption ảnh. Tuy nhiên, paper đo hiệu năng detector 3D trên KITTI-C, nuScenes-C và Waymo-C, nên không thể so trực tiếp với các proxy của nhóm.

## 4. Đánh giá luật mới trên sáu ảnh test

Luật mới dùng `noise_sigma`, `blur_norm` và `streak_ratio`; ngưỡng được hiệu chuẩn trên sáu ảnh baseline đầu, rồi báo cáo trên sáu ảnh còn lại. Bảng dưới lấy từ `results/flags_compare.csv`; mỗi ảnh tương ứng khoảng 17 điểm phần trăm.

| Điều kiện [Tự đo] | Luật cũ: `flag_any` | Luật mới: `flag_any` | Kết quả chính |
|---|---:|---:|---|
| Baseline | 0% | 0% | Không tăng cờ trên tập test nhỏ |
| Noise σ = 5 / 10 / 20 / 40 | 0% / 0% / 0% / 0% | 100% / 100% / 100% / 100% | Cờ nhiễu |
| Rain 200 / 600 vệt | 0% / 0% | 0% / 0% | Chưa phát hiện mưa nhẹ |
| Rain 1.200 / 2.400 vệt | 0% / 0% | 100% / 100% | Cờ mưa |
| Night ×0,6 | 100% | 0% | Hết nhầm tối là nhoè, nhưng bị bỏ sót |
| Glare +60 | 0% | 100% | Cờ blur giả do chuẩn hoá quá mức |

**[Tự đo]** Luật mới giải quyết được mục tiêu chính: bắt được noise ở mọi mức và mưa từ 1.200 vệt, trong khi baseline vẫn 0%. Tuy nhiên, `blur_norm = blur_score / mean_gray²` có hai đánh đổi quan trọng: bỏ sót night ×0,6 dù ORB giảm mạnh, và gắn cờ blur cho glare +60 dù `blur_score` hầu như không đổi.

## 5. Engineering decision và trade-off

**Quyết định đề xuất.** **[Giả thuyết]** Dùng health score như tín hiệu giám sát mềm: khi có cờ, giảm trọng số camera, tăng sử dụng cảm biến dự phòng hoặc yêu cầu kiểm tra thêm. Không dùng score này như một bộ quyết định độc lập cho phanh/lái hoặc để tuyên bố camera an toàn.

| Khía cạnh | Bằng chứng và đánh đổi |
|---|---|
| Độ bao phủ corruption | **[Tự đo]** Luật mới bắt noise và mưa nặng tốt hơn luật cũ, nhưng chưa bắt được mưa 200–600 vệt. Hạ ngưỡng mưa có thể tăng cờ giả vì ảnh sạch đã có các nét dọc như cột và vạch đường. |
| Đúng nguyên nhân | **[Tự đo]** `blur_norm` sửa nhầm lẫn tối → nhoè, nhưng tạo nhầm lẫn glare → nhoè. **[Giả thuyết]** Chuẩn hoá theo độ tương phản thay vì `mean_gray²` có thể giảm tác dụng phụ này. |
| Chi phí thời gian | **[Tự đo]** Năm metric dùng trong luật mới (`blur_norm`, `noise_sigma`, `streak_ratio`, `mean_gray`, `sat_ratio`) tổng cộng khoảng 0,37 ms/frame ở ảnh 256×96 trên CPU laptop. Kết quả chưa được đo trên phần cứng nhúng của xe. |
| Độ tin cậy | **[Tự đo]** Chỉ có 6 ảnh test, không có ground truth và không chạy detector. **[Giả thuyết]** Ngưỡng hiện tại không nên chuyển nguyên trạng sang camera, cảnh đêm hoặc thời tiết khác. |

## 6. Giới hạn và hướng tiếp theo

- **[Tự đo]** Dữ liệu chỉ gồm 12 ảnh nhỏ; mô phỏng dùng blur đều, night nhân độ sáng, nhiễu Gaussian sau 8-bit và vệt mưa thẳng, nên chưa đại diện đầy đủ cho camera thật.
- **[Tự đo]** Luật cũ được hiệu chuẩn trên toàn bộ baseline, còn luật mới chỉ dùng sáu ảnh calibration; do đó các tỷ lệ cờ chưa phải đánh giá độc lập ngoài miền dữ liệu.
- **[Giả thuyết]** Cần tăng tập hold-out, dùng hướng vệt để tách mưa khỏi cấu trúc cảnh và kiểm chứng mối liên hệ giữa health score với lỗi detector/fusion trên phần cứng mục tiêu.

## Tài liệu và bằng chứng

- `notes/failure_case.md` — nội dung được cập nhật trong commit nêu trên.
- `results/summary.csv`, `results/flags_old.csv`, `results/flags_compare.csv`, `results/latency.csv` — số đo và bảng cờ.
- Dong et al., [*Benchmarking Robustness of 3D Object Detection to Common Corruptions*](https://openaccess.thecvf.com/content/CVPR2023/html/Dong_Benchmarking_Robustness_of_3D_Object_Detection_to_Common_Corruptions_CVPR_2023_paper.html), CVPR 2023.
