"""Các điều kiện suy giảm camera (T1). Mỗi hàm: f(img_bgr_uint8, level_param, rng) -> img.
Tên mức lỗi = tham số thật (không dùng "mức 1")."""
import cv2
import numpy as np


def _k(img):
    """Hệ số theo độ phân giải: tham số blur/rain định nghĩa ở chuẩn 640 px rộng, ảnh nhỏ hơn thì co lại tương ứng."""
    return img.shape[1] / 640.0


def blur(img, sigma, rng):
    return cv2.GaussianBlur(img, (0, 0), sigma * _k(img))


def night(img, scale, rng):
    """Thiếu sáng: nhân độ sáng tuyến tính rồi lượng tử hoá lại 8-bit (không thêm nhiễu)."""
    return np.clip(img.astype(np.float32) * scale, 0, 255).astype(np.uint8)


def glare(img, amp, rng):
    """Chói: cộng một vầng sáng Gaussian (giống mặt trời/đèn pha), biên độ amp (0-255)."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s = 0.25 * w
    g = amp * np.exp(-((xx - 0.5 * w) ** 2 + (yy - 0.3 * h) ** 2) / (2 * s * s))
    return np.clip(img.astype(np.float32) + g[..., None], 0, 255).astype(np.uint8)


def noise(img, sigma, rng):
    """Nhiễu cảm biến (Gaussian, đơn vị mức xám 0-255)."""
    return np.clip(img.astype(np.float32) + rng.normal(0, sigma, img.shape), 0, 255).astype(np.uint8)


def rain(img, n_streaks, rng):
    """Vệt mưa: n_streaks đoạn thẳng sáng, hơi nghiêng, làm mềm nhẹ, trộn alpha 0.5."""
    h, w = img.shape[:2]
    k = _k(img)
    n_streaks = n_streaks * (w * h) / (640 * 360)   # số vệt theo diện tích ảnh
    layer = np.zeros((h, w), np.float32)
    for _ in range(int(round(n_streaks))):
        x, y, L = int(rng.integers(0, w)), int(rng.integers(0, h)), int(rng.integers(10, 25))
        L = max(2, int(round(L * k)))
        cv2.line(layer, (x, y), (x + int(0.17 * L), y + L), 1.0, 1)
    a = 0.5 * np.clip(cv2.GaussianBlur(layer, (0, 0), 0.8) * 2, 0, 1)[..., None]
    return np.clip(img.astype(np.float32) * (1 - a) + 220 * a, 0, 255).astype(np.uint8)


# tên -> (hàm, danh sách tham số 4 mức, nhãn đơn vị)
DEGRADATIONS = {
    "blur":  (blur,  [1, 2, 4, 8],          "Gaussian sigma (px @640 rộng)"),
    "night": (night, [0.6, 0.35, 0.2, 0.1], "brightness x"),
    "glare": (glare, [60, 120, 180, 255],   "glare peak (+gray)"),
    "noise": (noise, [5, 10, 20, 40],       "noise sigma (gray)"),
    "rain":  (rain,  [200, 600, 1200, 2400], "streaks / frame @640x360"),
}
