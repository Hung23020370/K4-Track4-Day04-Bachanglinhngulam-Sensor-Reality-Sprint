# PLAN — Bước 1, 2, 3

## Bước 1 · Chốt đề (bảng "Nhóm cần chốt")
| Mục | Nội dung |
|---|---|
| Nền tảng, tính năng, sensor | Xe ADAS; giám sát sức khoẻ ảnh camera để quyết định giảm trọng số camera; camera |
| Failure case | Ảnh bị nhoè, thiếu sáng (night), chói (glare), nhiễu cảm biến, vệt mưa |
| Claim ban đầu | Cùng một ảnh, tăng mức blur/night/glare → blur_score và số keypoint ORB giảm; glare → sat_ratio tăng. **Giả thuyết cần kiểm tra:** noise và rain có làm blur_score giảm như blur không? |
| Metric và đơn vị | blur_score = var(Laplacian ảnh xám), không đơn vị; sat_ratio = tỷ lệ pixel xám ≥ 250; entropy (bit); mean_gray (0-255); orb_kp = số keypoint ORB (proxy) |
| Baseline và điều kiện lỗi | Baseline = ảnh gốc không lỗi; 5 loại lỗi × 4 mức, mỗi mức đặt tên theo tham số thật |
| Phân công 5 thành viên | Xem bảng cuối file |

Ghi chú trung thực: phần "noise/rain làm blur_score *tăng*" là điều nhóm **quan sát sau khi chạy**, không phải dự đoán trước.

## Bước 2 · Nguồn
**Nguồn chính (đã xác minh qua trang chính thức, cần nhóm đọc kỹ rồi điền các ô còn trống):**
- Dong và cộng sự, *Benchmarking Robustness of 3D Object Detection to Common Corruptions*, CVPR 2023.
  - Trang CVPR: https://openaccess.thecvf.com/content/CVPR2023/html/Dong_Benchmarking_Robustness_of_3D_Object_Detection_to_Common_Corruptions_CVPR_2023_paper.html
  - arXiv: https://arxiv.org/abs/2303.11040
  - Code: https://github.com/thu-ml/3D_Corruptions_AD (một số nguồn ghi tài khoản `kkkcx`; nhóm tự mở link để xác nhận, rồi ghi **commit/version** đã xem: `____`)

**Paper cho biết (theo abstract, nhóm chưa đọc phần thân bài):** thiết kế 27 loại corruption cho cả LiDAR và camera, tạo ba benchmark KITTI-C, nuScenes-C, Waymo-C, đánh giá 24 mô hình 3D detection; kết luận gồm camera-only rất dễ tổn thương trước corruption ảnh.

| Câu hỏi khi đọc nguồn | Ghi chép |
|---|---|
| Phương pháp nhận gì và tạo gì? | Input → output: `____` (đọc phần Method) |
| Nguồn đo chất lượng bằng gì? | Metric/dataset của paper: `____` (đọc phần Experiments) |
| Chạy được ở lớp không? | Không: cần dataset và model detection lớn → nhóm dùng benchmark mô phỏng nhỏ |
| Nhóm tái hiện phần nào? | Chỉ **ý tưởng** "tạo corruption có kiểm soát trên cùng dữ liệu"; **không** tái hiện số của paper. Metric là **proxy**, không phải mAP |
| Limitation do nguồn nêu | `____` (chỉ điền những gì đọc thấy trong paper) |

Lý do chuyển sang mô phỏng: repo gốc đánh giá detector 3D trên dataset lớn, không khả thi trong 120 phút; proxy blur_score/sat_ratio/entropy/orb_kp vẫn kiểm tra được claim "ảnh xấu đi thì chỉ số nào đổi". Proxy này **chưa** chứng minh mAP của detector giảm bao nhiêu.

## Bước 3 · Thiết kế benchmark
- Dữ liệu: 12 ảnh đường thật trong `data/images/` (256×96 px, giữ nguyên độ phân giải). Nguồn/giấy phép: `____` (nhóm điền). Nếu thư mục rỗng, script tự dùng cảnh tổng hợp `make_scene`.
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

## Phân công 3 thành viên (điền tên)
| Vai | Người | Việc chính | Phụ trách pitch |
|---|---|---|---|
| A · Nguồn & phân tích | | Đọc paper/repo, điền các ô `____` ở Bước 2; viết/kiểm tra `notes/failure_case.md` (tách rõ: tự đo / nguồn nói / giả thuyết); trade-off | Problem + Failure case |
| B · Dữ liệu & chạy benchmark | | Kiểm tra `degrade.py` (tham số có thực tế không); tìm ảnh thật cho `data/images/` nếu có; chạy lại, lưu log/plot, đối chiếu số trong `failure_case.md` | Benchmark |
| C · Metric & cải tiến | | Kiểm tra `metrics.py` + luật cờ; làm cải tiến (ước lượng nhiễu, chuẩn hoá theo độ sáng); nếu còn thời gian thêm detector confidence; giữ repo gọn, điền `TEAMMATES.md` | Method + Engineering decision |

Cả 3 người đều nộp báo cáo/slide riêng nên mỗi người phải giải thích được toàn bộ luồng, không chỉ phần mình.

Mốc thời gian gợi ý: 0-15 phút chốt đề (cả nhóm) · 15-45 A đọc nguồn, B+C chạy thử baseline · 45-95 B chạy lỗi, C làm luật/cải tiến, A viết failure case · 95-115 cả nhóm đối chiếu số và tập pitch.
