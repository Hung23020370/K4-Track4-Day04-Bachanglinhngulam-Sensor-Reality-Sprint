# Sensor Reality Sprint — T1: Sức khoẻ camera ADAS

Nền tảng: xe ADAS · Sensor: camera · Tính năng chịu ảnh hưởng: giám sát chất lượng ảnh để quyết định giảm trọng số camera.

## Chạy lại
```bash
pip install -r requirements.txt
python src/run_benchmark.py --n 12 --seed 0     # ~vài chục giây, CPU
```
- Nếu `data/images/` có ảnh `.jpg/.png` thì dùng ảnh đó (giữ nguyên độ phân giải, hoặc `--width 640` để resize); nếu rỗng thì dùng **cảnh đường tổng hợp** (`src/make_scene.py`). Chỉ dùng ảnh được phép chia sẻ.
- Đối chiếu số trong `notes/failure_case.md`: `python tools/check_numbers.py`.
- Đầu ra trong `results/`: `metrics.csv` (từng ảnh), `summary.csv`, `flags.csv`, `trend.png`, `before_after.png`, `run.log`.
- Phiên bản đã chạy: xem dòng đầu `results/run.log`.

## Cấu trúc
| Đường dẫn | Nội dung |
|---|---|
| `PLAN.md` | Bước 1-3: claim, metric, nguồn, thiết kế benchmark, phân công |
| `notes/failure_case.md` | Bước 5: failure case, limitation, cải tiến |
| `src/degrade.py` | 5 loại lỗi × 4 mức (blur, night, glare, noise, rain) |
| `src/metrics.py` | 5 metric: blur_score, sat_ratio, entropy, mean_gray, orb_kp |
| `src/run_benchmark.py` | chạy toàn bộ, ghi bảng/plot/log |
| `reports/` | (chưa làm) 5 bản báo cáo/slide riêng của 5 thành viên |
| `TEAMMATES.md` | họ tên + MSSV 5 thành viên |
