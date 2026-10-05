"""Metric cho T1. Cùng một hàm cho baseline và mọi điều kiện lỗi.
- blur_score  : phương sai Laplacian của ảnh xám (CAO = nét). Proxy cho độ nét.
- sat_ratio   : tỷ lệ pixel xám >= 250 (CAO = chói/cháy sáng).
- entropy     : entropy Shannon histogram xám (bit). Proxy cho lượng thông tin tương phản.
- mean_gray   : độ sáng trung bình (0-255).
- orb_kp      : số keypoint ORB (tối đa 5000). Proxy cho tính năng dựa trên feature (VO/SLAM).
KHÔNG metric nào ở đây là mAP/độ chính xác detector."""
import cv2
import numpy as np

_ORB = cv2.ORB_create(nfeatures=5000)


def compute(img_bgr: np.ndarray) -> dict:
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    p = np.bincount(g.ravel(), minlength=256) / g.size
    p = p[p > 0]
    return {
        "blur_score": float(cv2.Laplacian(g, cv2.CV_64F).var()),
        "sat_ratio": float((g >= 250).mean()),
        "entropy": float(-(p * np.log2(p)).sum()),
        "mean_gray": float(g.mean()),
        "orb_kp": int(len(_ORB.detect(g, None))),
    }
