# Báo cáo cá nhân — Sensor Reality Sprint, T1: Sức khoẻ camera ADAS

| | |
|---|---|
| Họ tên | `Nguyễn Công Thịnh` |
| MSSV | `2A202602781` |
| Nhóm | `Ba chàng lính ngự lâm` |
| Vai trò | **Nguồn & dữ liệu** — đọc paper/repo, nghiên cứu các phương pháp cho bài toán, ghi nguồn và giấy phép dữ liệu |

---

## 1. Bài toán

- **Nền tảng:** xe ADAS có camera phía trước.
- **Tính năng chịu ảnh hưởng:** một bộ "giám sát sức khoẻ camera" nhìn chất lượng ảnh để quyết định có nên **giảm trọng số camera** trong fusion hay không.
- **Câu hỏi:** khi ảnh bị suy giảm (nhoè, tối, chói, nhiễu, mưa), các chỉ số chất lượng ảnh đơn giản có phát hiện được không, và loại lỗi nào lọt qua?
- **Claim ban đầu:** tăng mức blur/night/glare thì `blur_score` và số keypoint ORB giảm, còn glare làm `sat_ratio` tăng. Giả thuyết cần kiểm tra: noise và rain có làm `blur_score` giảm như blur không?

## 2. Nguồn tham khảo (phần tôi phụ trách)

**Paper:** Y. Dong, C. Kang, J. Zhang, Z. Zhu, Y. Wang, X. Yang, H. Su, X. Wei, J. Zhu. *Benchmarking Robustness of 3D Object Detection to Common Corruptions*, CVPR 2023. arXiv: 2303.11040 (v1, 20/03/2023).
**Code:** https://github.com/thu-ml/3D_Corruptions_AD, giấy phép MIT, commit đã xem `48c23f7` (09/10/2024).

| Câu hỏi | Paper/repo trả lời |
|---|---|
| Làm gì? | Tạo **corruption tổng hợp có kiểm soát** trên dữ liệu lái xe sạch rồi đo detector 3D giảm hiệu năng bao nhiêu. |
| Input → output | LiDAR point cloud (N×4/N×5) và ảnh camera đa góc nhìn → bản bị lỗi, **27 loại × 5 mức** (repo: `severity` 1-5, `seed` cố định). 27 loại chia 5 cấp: weather, sensor, motion, object, alignment. |
| Lỗi camera gần với nhóm | Gaussian noise, motion blur, rain, fog, snow, strong sunlight. |
| Đo bằng gì? | Hiệu năng **detector**: AP (KITTI-C), mAP và NDS (nuScenes-C, Waymo-C), cùng RCE (% hiệu năng giảm so với dữ liệu sạch). 24 model gồm LiDAR-only, camera-only và fusion. |
| Kết luận | (1) Lỗi cấp motion nguy hiểm nhất. (2) Fusion LiDAR-camera bền hơn. (3) **Camera-only rất dễ tổn thương** trước corruption ảnh. |
| Limitation tác giả nêu | Không thể liệt kê hết lỗi thật; lỗi tổng hợp luôn có khoảng cách với dữ liệu thật (chỉ kiểm chứng với thời tiết); một số lỗi LiDAR xoá vật thể nhưng ground truth không đổi. |

**Nhóm lấy gì và không lấy gì:**
- **Lấy:** ý tưởng *cùng ảnh gốc → nhiều loại lỗi × nhiều mức, seed cố định → cùng một hàm đo*.
- **Không lấy:** dataset (KITTI/nuScenes/Waymo), detector 3D và mAP. Những phần này cần GPU và dataset lớn, không khả thi trong 120 phút. Vì vậy **không so trực tiếp** số của nhóm với số của paper.
- **Khác biệt:** nhóm dùng 4 mức thay vì 5, một camera 2D thay vì 3D đa sensor. Lỗi `night` (giảm sáng) là nhóm tự thêm, không có trong danh sách của paper.

## 3. Dữ liệu (phần tôi phụ trách)

- **Nguồn:** bộ "cityscapes dataset" trên Kaggle (https://www.kaggle.com/datasets/shuvoalok/cityscapes). Đây là bản đăng lại, đã thu nhỏ và tách sẵn ảnh/mask theo train/val, của **Cityscapes** (Cordts và cộng sự, CVPR 2016).
- **Cách lấy:** 12 ảnh đầu `train1.png … train12.png` trong phần ảnh của tập train (bỏ mask), chép vào `data/images/` và giữ nguyên **256×96 px**.
- **Giấy phép:** Cityscapes chỉ cho dùng phi thương mại (nghiên cứu, giảng dạy), phải trích dẫn paper gốc, không phân phối lại bộ dữ liệu. Repo chỉ giữ 12 ảnh minh hoạ cho bài tập. Trường "License" trên trang Kaggle: `<kiểm tra và điền>`.
- **Đặc điểm cần biết khi đọc kết quả:** ảnh ban ngày, trời tốt, đường phố thành phố ở Đức nên baseline là "sạch". Ảnh khá tối (mean_gray ≈ 64/255) và đã bị thu nhỏ mạnh từ bản gốc 2048×1024 nên ít chi tiết.

## 4. Thiết kế benchmark (toàn bộ luồng)

```
data/images (12 ảnh) ─► degrade.py: 5 loại lỗi × 4 mức ─► metrics.py: 5 metric ─► luật cờ ─► results/
```

| Lỗi | Tham số 4 mức | Cách mô phỏng |
|---|---|---|
| blur | Gaussian σ = 1, 2, 4, 8 px (chuẩn 640 px rộng; ảnh 256 px nên σ thực = σ×0,4) | làm nhoè đều |
| night | độ sáng ×0,6 / 0,35 / 0,2 / 0,1 | nhân tuyến tính, không thêm nhiễu |
| glare | vầng sáng +60 / 120 / 180 / 255 mức xám | Gaussian sáng ở phần trên ảnh |
| noise | σ = 5 / 10 / 20 / 40 mức xám | nhiễu Gaussian cộng sau 8-bit |
| rain | 200 / 600 / 1200 / 2400 vệt mỗi frame 640×360 (co theo diện tích) | vệt thẳng sáng, trộn alpha |

**Metric (đều là proxy, không phải mAP):**
- `blur_score`: phương sai Laplacian (cao = nét)
- `sat_ratio`: tỷ lệ pixel ≥ 250
- `entropy`: bit
- `mean_gray`: 0-255
- `orb_kp`: số keypoint ORB, proxy cho VO/SLAM

**Luật cờ:**
- cờ blur nếu `blur_score` < 0,5 × median baseline (= **350,8**)
- cờ tối nếu `mean_gray` < 0,5 × median baseline (= **32,6**)
- cờ chói nếu `sat_ratio` > 0,05

Ngưỡng blur và tối được hiệu chuẩn trên chính baseline. Chạy lại bằng: `python src/run_benchmark.py --n 12 --seed 0` rồi đối chiếu số với `python tools/check_numbers.py`.

## 5. Kết quả (tự đo, `results/summary.csv` và `results/flags.csv`)

| Điều kiện | blur_score (× baseline) | orb_kp | mean_gray | sat_ratio | % frame bị cờ |
|---|---|---|---|---|---|
| baseline | 717,7 (1,0×) | 196 | 64,4 | 0,0015 | 0% |
| blur σ=1 / σ=2 | 547,8 (0,76×) / 91,0 (0,13×) | 176 / 87 | 64,4 | — | 8% / 100% |
| night ×0,6 / ×0,35 | 259,9 (0,36×) / 89,4 (0,12×) | 76 / 15 | 38,3 / 22,1 | 0 | 83% (chỉ cờ blur) / 100% |
| glare +60 / +120 / +255 | 715,1 / 686,7 / 391,6 | 195 / 197 / 94 | 95 / 126 / 184 | 0,013 / 0,048 / 0,270 | 0% / 42% / 100% |
| **noise σ=5 / 10 / 20 / 40** | **942,8 (1,3×) / 1607 (2,2×) / 4127 (5,7×) / 12553 (17,5×)** | 207 / 260 / 426 / 655 | ≈ 64 | ≈ 0,001 | **0% ở cả 4 mức** |
| **rain 200 / 1200 / 2400** | **774,1 (1,08×) / 1035 (1,44×) / 1279 (1,78×)** | 215 / 287 / 359 | 65 / 70 / 76 | ≈ 0,001 | **0% ở cả 4 mức** |

Hình: `results/trend.png` (metric theo mức lỗi) và `results/before_after.png` (ảnh trước/sau).

**Claim ban đầu đúng một phần:**
- blur, night và glare mạnh làm `blur_score` và `orb_kp` giảm như dự đoán. glare làm `sat_ratio` tăng tới 180 lần.
- **noise và rain thì ngược lại.** Hai lỗi này làm `blur_score` và `orb_kp` **tăng**, nên luật cờ coi ảnh xấu là "nét hơn" và không gắn cờ frame nào. Điều này nhóm quan sát sau khi chạy, không dự đoán trước.

## 6. Failure case và cách hiểu đúng

Tách rõ ba loại thông tin:

- **Nhóm tự đo:** nhiễu σ=10 (mức thực tế với camera rẻ hoặc ánh sáng yếu) làm `blur_score` tăng 2,2× và ORB keypoint tăng 32%. Luật cờ bỏ sót 100% frame nhiễu và 100% frame mưa.
  Luật blur cũng nhầm "tối" với "nhoè": ở night ×0,6, 83% frame bị cờ *blur* trong khi cờ *tối* chưa bật (38,3 > 32,6).
- **Nguồn nói:** camera-only detector rất dễ tổn thương trước corruption ảnh, trong đó có noise và rain (Dong và cộng sự, 2023). Đây là kết luận trên mAP/NDS với dataset của paper.
- **Giả thuyết (chưa đo):** Laplacian khuếch đại tần số cao nên không phân biệt được chi tiết thật với nhiễu hoặc vệt mưa. Thuật toán dựa trên feature có thể bám vào keypoint giả do nhiễu.
  Ghép với kết luận của paper: một bộ giám sát chỉ dựa vào `blur_score` có thể **giữ nguyên trọng số camera đúng lúc detector camera đang yếu nhất**. Muốn khẳng định cần chạy detector thật.

## 7. Limitation

- **Dữ liệu:** 12 ảnh nhỏ 256×96, chỉ ban ngày, một thành phố; không có ground truth và không chạy detector nên không kết luận được về mAP.
- **Mô phỏng:** blur đều (không phải motion blur), night không có nhiễu đi kèm, noise cộng sau 8-bit (không qua ISP), mưa là vệt thẳng. noise σ=20 và σ=40 nặng hơn camera thật.
- **Ngưỡng in-sample:** đổi cảnh hoặc camera thì phải hiệu chuẩn lại.
- **Không so được với paper:** khác dataset, khác metric (proxy so với mAP), 4 mức so với 5 mức. Tham số co theo chuẩn 640 px là lựa chọn của nhóm.

## 8. Đề xuất cải tiến

1. Thêm **ước lượng mức nhiễu** làm metric thứ hai. Luật mới: `blur_score` thấp **hoặc** nhiễu cao → giảm trọng số camera.
2. **Chuẩn hoá `blur_score` theo độ sáng** để không nhầm tối với nhoè.
3. Thêm detector confidence (vd. YOLO) vào benchmark để nối proxy với hiệu năng thật, giống cách paper đo bằng mAP.
4. Mở rộng dữ liệu: lấy thêm ảnh từ tập val của Cityscapes và dùng ảnh thời tiết xấu thật để kiểm tra khoảng cách giữa lỗi tổng hợp và lỗi thật, đúng limitation paper nêu.

**Tiêu chí kiểm chứng vòng sau:** tỷ lệ cờ ở noise σ ≥ 10 và rain ≥ 1200 vệt tăng khỏi 0%, trong khi baseline vẫn ≈ 0%.

## 9. Đóng góp cá nhân

- Đọc paper và repo, điền toàn bộ các ô còn trống ở Bước 2 của `PLAN.md`: phương pháp, metric/dataset, limitation, commit đã xem. Sửa lại tài khoản repo cho đúng (`thu-ml`).
- Xác định và ghi nguồn, cách lấy và giấy phép của 12 ảnh trong `PLAN.md` (Bước 3) và `notes/failure_case.md`. Bổ sung limitation về dữ liệu.
- So sánh thiết kế benchmark của nhóm với paper để chỉ rõ phần tái hiện và phần không tái hiện.

## Tài liệu tham khảo

1. Y. Dong và cộng sự, "Benchmarking Robustness of 3D Object Detection to Common Corruptions", CVPR 2023. https://arxiv.org/abs/2303.11040
2. thu-ml/3D_Corruptions_AD, commit `48c23f7`. https://github.com/thu-ml/3D_Corruptions_AD
3. M. Cordts và cộng sự, "The Cityscapes Dataset for Semantic Urban Scene Understanding", CVPR 2016. https://www.cityscapes-dataset.com
4. Kaggle, "cityscapes dataset" (shuvoalok). https://www.kaggle.com/datasets/shuvoalok/cityscapes
