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
- Chưa đo latency. **Giả thuyết** nguyên nhân: Laplacian khuếch đại nhiễu tần số cao nên không tách được "chi tiết thật" khỏi "nhiễu".

## Đề xuất cải tiến / fallback (nối với failure ở trên)
1. Thêm **ước lượng nhiễu** làm metric thứ hai; luật cờ: blur_score thấp **hoặc** nhiễu cao → giảm trọng số camera.
2. Chuẩn hoá blur_score theo độ sáng trước khi so ngưỡng, để không nhầm "tối" với "nhoè".
3. Fallback: khi cờ bật, giảm trọng số camera trong fusion hoặc dựa vào LiDAR/radar (đề xuất thiết kế, chưa kiểm chứng).

**Đã chạy vòng thử tiếp theo** (vai C, chi tiết ở `notes/improvement.md`). Trên 6 ảnh test:
- noise được gắn cờ 100% ở cả 4 mức (trước: 0%);
- rain 1200 và 2400 vệt được gắn cờ 100%, nhưng rain 200 và 600 vẫn 0%;
- baseline vẫn 0%;
- tác dụng phụ: glare +60 nay bị cờ blur 100%.

Lưu ý: từ vòng này, `results/flags.csv` là luật mới; số của luật cũ ở trên nằm trong `results/flags_old.csv`.

**Kiểm chứng ở vòng thử tiếp theo (kỳ vọng ban đầu):** chạy lại `run_benchmark.py` với luật mới; kỳ vọng (cần kiểm tra, chưa đạt) là tỷ lệ cờ ở noise σ ≥ 10 và rain ≥ 1200 vệt tăng khỏi 0%, trong khi tỷ lệ cờ ở baseline vẫn ≈ 0%.
