"""Lấy ảnh từ video (dashcam/điện thoại của chính nhóm) bỏ vào data/images/.
Dùng:  python tools/extract_frames.py video.mp4 --n 12
Lấy n khung cách đều nhau, resize rộng 640 px. Chỉ dùng video nhóm tự quay hoặc được phép dùng."""
import argparse, os, cv2

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--n", type=int, default=12)
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "images"))
a = ap.parse_args()
cap = cv2.VideoCapture(a.video)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
assert total > 0, "không đọc được video"
os.makedirs(a.out, exist_ok=True)
for k in range(a.n):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int((k + 0.5) * total / a.n))
    ok, im = cap.read()
    if not ok:
        continue
    h, w = im.shape[:2]
    cv2.imwrite(os.path.join(a.out, f"frame_{k:02d}.jpg"), cv2.resize(im, (640, int(h * 640 / w))), [cv2.IMWRITE_JPEG_QUALITY, 95])
print("đã lưu vào", os.path.abspath(a.out))
