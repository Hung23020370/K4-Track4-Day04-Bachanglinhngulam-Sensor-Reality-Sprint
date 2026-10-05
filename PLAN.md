# PLAN — Bước 1, 2, 3

## Bước 1 · Chốt đề (bảng "Nhóm cần chốt")
| Mục | Nội dung |
|---|---|
| Nền tảng, tính năng, sensor | Xe ADAS; giám sát sức khoẻ ảnh camera để quyết định giảm trọng số camera; camera |
| Failure case | Ảnh bị nhoè, thiếu sáng (night), chói (glare), nhiễu cảm biến, vệt mưa |
| Claim ban đầu | Cùng một ảnh, tăng mức blur/night/glare → blur_score và số keypoint ORB giảm; glare → sat_ratio tăng. **Giả thuyết cần kiểm tra:** noise và rain có làm blur_score giảm như blur không? |
| Metric và đơn vị | blur_score = var(Laplacian ảnh xám), không đơn vị; sat_ratio = tỷ lệ pixel xám ≥ 250; entropy (bit); mean_gray (0-255); orb_kp = số keypoint ORB (proxy) |
| Baseline và điều kiện lỗi | Baseline = ảnh gốc không lỗi; 5 loại lỗi × 4 mức, mỗi mức đặt tên theo tham số thật |
| Phân công 4 thành viên | Xem bảng cuối file |

Ghi chú trung thực: phần "noise/rain làm blur_score *tăng*" là điều nhóm **quan sát sau khi chạy**, không phải dự đoán trước.

## Bước 2 · Nguồn
**Nguồn chính (đã xác minh qua trang chính thức):**
- Dong, Kang, Zhang, Zhu, Wang, Yang, Su, Wei, Zhu, *Benchmarking Robustness of 3D Object Detection to Common Corruptions* (bản arXiv thêm "in Autonomous Driving"), CVPR 2023.
  - Trang CVPR: https://openaccess.thecvf.com/content/CVPR2023/html/Dong_Benchmarking_Robustness_of_3D_Object_Detection_to_Common_Corruptions_CVPR_2023_paper.html
  - arXiv: https://arxiv.org/abs/2303.11040 (v1, 20/03/2023)
  - Code: https://github.com/thu-ml/3D_Corruptions_AD (tài khoản `thu-ml`, giấy phép MIT). Commit đã xem: `48c23f7` (`48c23f77fe82beab599f8248b7794928334a3fb5`, "Update README.md", 09/10/2024 — commit mới nhất trên nhánh mặc định khi tra ngày 05/10/2026).

**Paper cho biết (đọc abstract + phần Method/Experiments):** thiết kế 27 loại corruption cho cả LiDAR và camera, chia 5 cấp (weather, sensor, motion, object, alignment), mỗi loại 5 mức nghiêm trọng; tạo ba benchmark KITTI-C, nuScenes-C, Waymo-C, đánh giá 24 mô hình 3D detection. Kết luận chính: (1) corruption cấp motion nguy hiểm nhất, làm mọi model giảm mạnh; (2) model fusion LiDAR-camera bền hơn; (3) model camera-only rất dễ tổn thương trước corruption ảnh.

| Câu hỏi khi đọc nguồn | Ghi chép |
|---|---|
| Phương pháp nhận gì và tạo gì? | Input: dữ liệu sạch của dataset lái xe công khai — point cloud LiDAR (mảng N×4 hoặc N×5) và ảnh camera (đa góc nhìn). Output: bản bị corruption **tổng hợp** của chính dữ liệu đó, 27 loại × 5 mức nghiêm trọng (repo: hàm/lớp nhận `severity` 1-5 và `seed`, vd. `ImageAddSnow(severity, seed=2022)`). Phía camera có các lỗi gần với nhóm: Gaussian noise, motion blur, rain, fog, snow, strong sunlight. Sau đó đưa dữ liệu lỗi qua detector 3D đã train sẵn để đo độ giảm hiệu năng. |
| Nguồn đo chất lượng bằng gì? | Đo **hiệu năng detector**, không đo chất lượng ảnh: KITTI-C dùng AP (IoU 0,7 cho xe; 0,5 cho người đi bộ/xe đạp), 3.769 mẫu val, 24 corruption; nuScenes-C dùng mAP và NDS, 6.000 frame val, đủ 27 corruption; Waymo-C dùng mAP trên 202 cảnh val. Thêm **RCE** (Relative Corruption Error) = % hiệu năng giảm so với dữ liệu sạch. Model: 11 (KITTI-C), 10 (nuScenes-C), 3 (Waymo-C) — gồm LiDAR-only, camera-only, fusion. |
| Chạy được ở lớp không? | Không: cần dataset và model detection lớn → nhóm dùng benchmark mô phỏng nhỏ |
| Nhóm tái hiện phần nào? | Chỉ **ý tưởng** "tạo corruption có kiểm soát trên cùng dữ liệu, nhiều mức nghiêm trọng, seed cố định"; **không** tái hiện số của paper. Metric là **proxy**, không phải mAP/NDS. Khác biệt: nhóm dùng 4 mức thay vì 5, ảnh 2D đơn camera thay vì 3D đa sensor; lỗi "night" (giảm sáng) là nhóm tự thêm, không nằm trong danh sách corruption camera của paper. |
| Limitation do nguồn nêu | (1) Tác giả thừa nhận không thể liệt kê hết corruption ngoài đời thực; 27 loại chỉ là bộ thử thực dụng để đánh giá có kiểm soát. (2) Corruption là **tổng hợp** nên luôn có khoảng cách với dữ liệu thật; tác giả chỉ kiểm chứng cho trường hợp thời tiết, khi thấy hiệu năng trên thời tiết tổng hợp nhất quán với dữ liệu thời tiết xấu thật. (3) Một số corruption LiDAR (Cutout, FOV Lost) có thể xoá vật thể khỏi point cloud nhưng ground truth vẫn giữ nguyên, vì tác giả giữ giao thức đánh giá gốc. |

Lý do chuyển sang mô phỏng: repo gốc đánh giá detector 3D trên dataset lớn, không khả thi trong 120 phút; proxy blur_score/sat_ratio/entropy/orb_kp vẫn kiểm tra được claim "ảnh xấu đi thì chỉ số nào đổi". Proxy này **chưa** chứng minh mAP của detector giảm bao nhiêu.

## Bước 3 · Thiết kế benchmark
- Dữ liệu: 12 ảnh đường thật trong `data/images/` (256×96 px, giữ nguyên độ phân giải). Nguồn: bộ "cityscapes dataset" trên Kaggle (https://www.kaggle.com/datasets/shuvoalok/cityscapes), một bản đã xử lý lại (thu nhỏ, có ảnh + mask tách riêng, chia train/val) của **Cityscapes** gốc (Cordts và cộng sự, CVPR 2016, https://www.cityscapes-dataset.com). Lấy 12 ảnh đầu `train1..train12.png` trong phần ảnh (không lấy mask) của tập train. Giấy phép: Cityscapes chỉ cho dùng **phi thương mại** (nghiên cứu, giảng dạy), phải trích dẫn paper gốc, không được phân phối lại bộ dữ liệu → repo chỉ giữ 12 ảnh minh hoạ cho bài tập. Bản Kaggle là bản đăng lại của bên thứ ba; nhóm cần mở trang Kaggle để ghi lại trường "License" ghi trên đó. Nếu thư mục rỗng, script tự dùng cảnh tổng hợp `make_scene`.
- Tham số blur và số vệt mưa định nghĩa ở chuẩn 640 px rộng và được co theo độ phân giải ảnh.
- Mọi lỗi tạo từ **cùng ảnh gốc**, cùng hàm metric; seed cố định theo ảnh và mức.

| Điều kiện | Tham số thay đổi | Metric (đơn vị) | Bằng chứng | Cho phép kết luận |
|---|---|---|---|---|
| Baseline | Không lỗi | cả 5 metric | `results/summary.csv`, dòng baseline | Mốc so sánh |
| blur | Gaussian σ = 1, 2, 4, 8 px | blur_score, orb_kp | `trend.png`, `before_after.png` | Chênh lệch so với baseline |
| night | brightness ×0.6, 0.35, 0.2, 0.1 | mean_gray, blur_score, orb_kp | như trên | xu hướng theo mức tối |
| glare | vầng sáng Gaussian +60, 120, 180, 255 mức xám | sat_ratio, entropy | như trên | xu hướng theo độ chói |
| noise | Gaussian σ = 5, 10, 20, 40 mức xám | blur_score, entropy, orb_kp | như trên | kiểm tra metric có bị đánh lừa |
| rain | 200, 600, 1200, 2400 vệt/frame | blur_score, orb_kp | như trên | như trên |

Luật cờ (health rule) dùng để đo "metric có phát hiện được lỗi không": cờ blur nếu blur_score < 0.5×median baseline; cờ tối nếu mean_gray < 0.5×median baseline; cờ chói nếu sat_ratio > 0.05. Ngưỡng hiệu chuẩn **trên chính baseline** (in-sample).

**Luật mới (vai C, xem `notes/improvement.md`):** cờ blur dùng `blur_norm = blur_score / mean_gray²` < 0.5×median baseline; thêm cờ nhiễu `noise_sigma` > 2×median baseline; thêm cờ mưa `streak_ratio` > 2×median baseline và không có cờ nhiễu. Ngưỡng hiệu chuẩn trên baseline 6 ảnh đầu, báo cáo tỷ lệ cờ trên 6 ảnh sau. Luật cũ vẫn được tính lại (`results/flags_old.csv`) để so sánh.

## Phân công 3 thành viên (điền tên)
| Vai | Người | Việc chính | Phụ trách pitch |
|---|---|---|---|
| A · Nguồn & dữ liệu | | Đọc paper/repo và điền mọi ô ____ ở Bước 2. Ghi nguồn và giấy phép của 12 ảnh. Điền TEAMMATES.md | Problem + Failure case |
| B · Dữ liệu & chạy benchmark | | Kiểm tra `degrade.py` (tham số có thực tế không); tìm ảnh thật cho `data/images/` nếu có; chạy lại, lưu log/plot, đối chiếu số trong `failure_case.md` | Benchmark |
| C · Failure case & trade-off | | Kiểm tra `metrics.py` + luật cờ; làm cải tiến (ước lượng nhiễu, chuẩn hoá theo độ sáng); nếu còn thời gian thêm detector confidence; giữ repo gọn, điền `TEAMMATES.md` | Method + Engineering decision |

Cả 3 người đều nộp báo cáo/slide riêng nên mỗi người phải giải thích được toàn bộ luồng, không chỉ phần mình.

Mốc thời gian gợi ý: 0-15 phút chốt đề (cả nhóm) · 15-45 A đọc nguồn, B+C chạy thử baseline · 45-95 B chạy lỗi, C làm luật/cải tiến, A viết failure case · 95-115 cả nhóm đối chiếu số và tập pitch.
