# Bước 5 · Failure case, limitation và trade-off ADAS

- **[Tự đo]** Nhãn này chỉ kết quả nhóm chạy lại, và các số bên dưới đối chiếu với `results/summary.csv`, `results/flags_old.csv`, `results/flags_compare.csv` hoặc `results/latency.csv`.
- **[Nguồn nói]** Nhãn này chỉ điều tài liệu hoặc giấy phép của nguồn khẳng định, chứ không phải kết quả benchmark của nhóm.
- **[Giả thuyết]** Nhãn này chỉ suy luận hay khuyến nghị chưa được đo bằng detector hoặc thử nghiệm xe thật.

## Benchmark và phạm vi

- **[Tự đo]** Benchmark dùng 12 ảnh đường `data/images/train1..12.png`, độ phân giải 256×96 px, giữ nguyên độ phân giải và seed 0.
- **[Nguồn nói]** Các ảnh là bản đã xử lý của Cityscapes lấy qua [Kaggle](https://www.kaggle.com/datasets/shuvoalok/cityscapes), còn [Cityscapes](https://www.cityscapes-dataset.com) yêu cầu dùng phi thương mại, trích dẫn bài báo gốc và không phân phối lại toàn bộ dữ liệu.
- **[Tự đo]** Mỗi điều kiện được đo bằng `blur_score`, `sat_ratio`, `entropy`, `mean_gray`, `orb_kp`, `noise_sigma`, `blur_norm` và `streak_ratio`, là proxy của ảnh chứ không phải mAP hoặc độ chính xác detector.
- **[Tự đo]** Luật cũ đặt cờ blur, tối và chói, trong khi luật mới thêm cờ nhiễu và mưa, chuẩn hoá blur theo độ sáng, rồi hiệu chuẩn trên 6 ảnh đầu và báo cáo trên 6 ảnh sau.
- **[Nguồn nói]** Dong và cộng sự (CVPR 2023) đánh giá corruption bằng hiệu năng detector 3D trên KITTI-C, nuScenes-C và Waymo-C, nên các proxy của nhóm không tái hiện trực tiếp kết quả của paper.

## Failure case chính: nhiễu và mưa làm ảnh xấu trông “nét” hơn

- **[Tự đo]** Baseline có `blur_score` 717,7 và 196 ORB keypoint theo `summary.csv`.
- **[Tự đo]** Nhiễu Gaussian σ = 5, 10, 20 và 40 làm `blur_score` lần lượt thành 942,8, 1.607,3, 4.126,8 và 12.552,6, tương ứng 1,3×, 2,2×, 5,7× và 17,5× baseline.
- **[Tự đo]** Cùng các mức nhiễu đó, ORB keypoint lần lượt là 207, 260, 426 và 655, trong khi baseline là 196.
- **[Tự đo]** Luật cũ gắn `flag_any` 0% cho cả bốn mức nhiễu và cho baseline.
- **[Tự đo]** Mưa 200, 600, 1.200 và 2.400 vệt làm `blur_score` lần lượt thành 774,1, 884,1, 1.034,5 và 1.278,9, còn luật cũ vẫn gắn `flag_any` 0% ở mọi mức.
- **[Tự đo]** Trong phạm vi proxy này, nhiễu và vệt mưa làm tín hiệu Laplacian tăng nên luật cũ bỏ sót ảnh đã bị corruption.
- **[Giả thuyết]** Keypoint do nhiễu có thể kém ổn định hơn keypoint do cấu trúc cảnh, nhưng cần chạy visual odometry, SLAM hoặc detector thật mới kiểm tra được tác động đó.
- **[Nguồn nói]** Dong và cộng sự kết luận mô hình camera-only dễ tổn thương trước corruption ảnh, nhưng đây là kết luận theo detector và dữ liệu của paper chứ không phải phép so sánh trực tiếp với các số ở đây.

## Kiểm tra các failure case khác

| Điều kiện, toàn bộ 12 ảnh | Số đo chính | Cờ luật cũ | Nhãn |
|---|---:|---:|---|
| night ×0,6 | `blur_score` 259,9; `mean_gray` 38,3; ORB 76 | blur 83%; tối 0%; bất kỳ 83% | Tự đo |
| glare +60 | `blur_score` 715,1; `mean_gray` 95,3 | bất kỳ 0% | Tự đo |
| glare +120 / +180 / +255 | `flag_any` 42% / 83% / 100% | chói là 42% / 83% / 100% | Tự đo |
| Gaussian blur σ = 1 / 2 / 4 / 8 | – | `flag_any` 8% / 100% / 100% / 100% | Tự đo |

- **[Tự đo]** Ở night ×0,6, luật cũ bật cờ blur nhưng chưa bật cờ tối, nên `blur_score` thô nhầm thiếu sáng với nhoè.
- **[Tự đo]** Ở glare +60, luật cũ không bật cờ nào, còn ở glare +120, +180 và +255 tỷ lệ cờ chói lần lượt là 42%, 83% và 100%.
- **[Tự đo]** Các tỷ lệ 8%, 42% và 83% tương ứng 1, 5 và 10 trong 12 ảnh, nên không nên diễn giải chúng như ước lượng chính xác cho quần thể ảnh lái xe rộng hơn.

## Luật mới: bằng chứng trước và sau trên cùng 6 ảnh test

- **[Tự đo]** Bảng này dùng `flags_compare.csv`, trong đó cả luật cũ và luật mới đều được tính trên 6 ảnh test, nên mỗi ảnh tương đương khoảng 17 điểm phần trăm.

| Điều kiện | Mức | `flag_any` luật cũ | `flag_any` luật mới | Cờ mới bật | Nhãn |
|---|---|---:|---:|---|---|
| baseline | – | 0% | 0% | – | Tự đo |
| noise | σ = 5 / 10 / 20 / 40 | 0% / 0% / 0% / 0% | 100% / 100% / 100% / 100% | nhiễu | Tự đo |
| rain | 200 / 600 / 1.200 / 2.400 vệt | 0% / 0% / 0% / 0% | 0% / 0% / 100% / 100% | mưa từ 1.200 | Tự đo |
| blur | σ = 1 / 2 / 4 / 8 | 17% / 100% / 100% / 100% | 0% / 100% / 100% / 100% | blur từ σ = 2 | Tự đo |
| night | ×0,6 | 100% | 0% | – | Tự đo |
| night | ×0,35 / ×0,2 / ×0,1 | 100% / 100% / 100% | 100% / 100% / 100% | tối | Tự đo |
| glare | +60 | 0% | 100% | blur | Tự đo |
| glare | +120 / +180 / +255 | 67% / 83% / 100% | 100% / 100% / 100% | blur 100%; chói 67% / 83% / 100% | Tự đo |

- **[Tự đo]** Luật mới phát hiện toàn bộ noise σ = 5–40 và rain 1.200–2.400 vệt trên 6 ảnh test, đồng thời giữ baseline ở 0%.
- **[Tự đo]** Luật mới bỏ sót night ×0,6 dù ORB giảm từ 196 xuống 76 trên toàn bộ 12 ảnh, nên việc sửa đúng nguyên nhân cờ không đồng nghĩa đã bao phủ đủ rủi ro nhận thức.
- **[Tự đo]** Luật mới gắn cờ blur cho glare +60 dù `blur_score` chỉ giảm từ 717,7 xuống 715,1, cho thấy `blur_norm` theo `mean_gray²` sửa quá mức với ánh sáng cộng thêm.
- **[Giả thuyết]** Vì glare là offset sáng thay vì gain tối, chuẩn hoá theo độ tương phản có thể phù hợp hơn chuẩn hoá theo `mean_gray²`, nhưng lựa chọn này chưa được thử trong benchmark.

## Trade-off: khi nào nên và không nên dùng health score trong ADAS

- **[Tự đo]** Tổng thời gian trung bình của `noise_sigma`, `blur_norm`, `streak_ratio`, `mean_gray` và `sat_ratio` là 0,3655 ms/frame theo `latency.csv`, nhưng con số này chỉ đo trên CPU laptop với ảnh 256×96 px.
- **[Nguồn nói]** Dong và cộng sự báo cáo fusion LiDAR–camera bền hơn camera-only trước corruption, nên có cơ sở từ nguồn để xem chất lượng camera là tín hiệu hỗ trợ fusion chứ không phải bằng chứng duy nhất về an toàn.
- **[Giả thuyết]** Nên dùng health score như một tín hiệu giám sát mềm để giảm trọng số camera, tăng dự phòng cảm biến khác hoặc yêu cầu kiểm tra thêm khi score vượt ngưỡng đã được hiệu chuẩn và xác thực trong miền vận hành cụ thể.
- **[Giả thuyết]** Nên dùng score khi hệ thống có fallback độc lập và khi đã chứng minh trên dữ liệu hold-out rằng score liên hệ với lỗi detector, bỏ sót đối tượng và cờ giả.
- **[Giả thuyết]** Không nên dùng score này như bộ quyết định độc lập cho phanh, lái hoặc tuyên bố camera “an toàn”, vì benchmark chưa chạy detector, không có ground truth và chỉ gồm 12 ảnh.
- **[Giả thuyết]** Không nên chuyển thẳng ngưỡng hiện tại sang camera, cảnh đêm hoặc thời tiết khác, vì dữ liệu cho thấy hạ ngưỡng mưa có thể gần mức streak nền và glare +60 đã tạo cờ blur giả.
- **[Giả thuyết]** Trade-off đúng là chấp nhận một số cảnh báo thừa để tránh bỏ sót corruption quan trọng, nhưng mức đánh đổi chỉ nên được chốt sau khi đo false-positive, false-negative và hiệu năng detector trên dữ liệu đại diện.

## Giới hạn và bước kế tiếp

- **[Tự đo]** Benchmark chỉ có 12 ảnh nhỏ, trong đó luật mới đánh giá 6 ảnh test, nên các tỷ lệ cờ thay đổi theo bước khoảng 17 điểm phần trăm.
- **[Tự đo]** Mô phỏng dùng blur Gaussian đều, nhân sáng cho night, cộng nhiễu Gaussian sau 8-bit và vệt mưa thẳng, nên không đại diện đầy đủ cho camera và môi trường thật.
- **[Tự đo]** Các ngưỡng luật cũ hiệu chuẩn trên toàn bộ baseline, còn luật mới hiệu chuẩn trên 6 ảnh đầu, vì vậy kết quả chưa phải đánh giá độc lập ngoài miền dữ liệu này.
- **[Nguồn nói]** Paper cũng nêu corruption tổng hợp không thể bao quát hết lỗi ngoài đời thực và có khoảng cách với dữ liệu thời tiết thật.
- **[Giả thuyết]** Bước kế tiếp nên là tăng dữ liệu hold-out, đo detector và fusion trên phần cứng mục tiêu, rồi kiểm tra xem score có cải thiện quyết định fallback mà không tạo cờ giả quá mức hay không.
