"""Metric cho T1. Cùng một hàm cho baseline và mọi điều kiện lỗi.
- blur_score  : phương sai Laplacian của ảnh xám (CAO = nét). Proxy cho độ nét.
- sat_ratio   : tỷ lệ pixel xám >= 250 (CAO = chói/cháy sáng).
- entropy     : entropy Shannon histogram xám (bit). Proxy cho lượng thông tin tương phản.
- mean_gray   : độ sáng trung bình (0-255).
- orb_kp      : số keypoint ORB (tối đa 5000). Proxy cho tính năng dựa trên feature (VO/SLAM).
- noise_sigma : (cải tiến) ước lượng độ lệch chuẩn nhiễu, mức xám 0-255 (Immerkær 1996).
- blur_norm   : (cải tiến) blur_score / mean_gray^2, không đơn vị. Nhân độ sáng xk làm var(Laplacian)
                giảm k^2 lần, chia cho mean^2 khử ảnh hưởng đó để "tối" không bị nhầm thành "nhoè".
- streak_ratio: (cải tiến) tỷ lệ pixel thuộc nét sáng mảnh gần thẳng đứng: white top-hat kernel ngang 5x1,
                ngưỡng > 20 mức xám. Proxy cho vệt mưa; nhiễu cũng làm tăng nên luật cờ phải kết hợp noise_sigma.
KHÔNG metric nào ở đây là mAP/độ chính xác detector."""
import cv2
import numpy as np

_ORB = cv2.ORB_create(nfeatures=5000)
# kernel Immerkær: hiệu của hai Laplacian, triệt tiêu cấu trúc trơn, giữ lại nhiễu
_IMM = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float64)


def _entropy(g):
    p = np.bincount(g.ravel(), minlength=256) / g.size
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def _noise_sigma(g):
    h, w = g.shape
    r = cv2.filter2D(g.astype(np.float64), -1, _IMM)[1:-1, 1:-1]
    return float(np.sqrt(np.pi / 2) * np.abs(r).sum() / (6 * (w - 2) * (h - 2)))


_STREAK_K = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))


def _streak_ratio(g):
    return float((cv2.morphologyEx(g, cv2.MORPH_TOPHAT, _STREAK_K) > 20).mean())


def _blur_norm(g):
    return float(cv2.Laplacian(g, cv2.CV_64F).var() / max(g.mean(), 1.0) ** 2)


# tên -> hàm(ảnh xám) ; tách riêng để đo latency từng metric
METRIC_FNS = {
    "blur_score": lambda g: float(cv2.Laplacian(g, cv2.CV_64F).var()),
    "sat_ratio": lambda g: float((g >= 250).mean()),
    "entropy": _entropy,
    "mean_gray": lambda g: float(g.mean()),
    "orb_kp": lambda g: int(len(_ORB.detect(g, None))),
    "noise_sigma": _noise_sigma,
    "blur_norm": _blur_norm,
    "streak_ratio": _streak_ratio,
}


def gray(img_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)


def compute(img_bgr: np.ndarray) -> dict:
    g = gray(img_bgr)
    return {k: f(g) for k, f in METRIC_FNS.items()}
