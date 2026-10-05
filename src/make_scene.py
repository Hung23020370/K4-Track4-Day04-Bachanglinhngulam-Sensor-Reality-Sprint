"""Tạo cảnh đường giả lập (dữ liệu tổng hợp) khi nhóm chưa có ảnh thật.
Mỗi seed cho một cảnh khác nhau. Ảnh BGR uint8, 640x360."""
import cv2
import numpy as np


def make_scene(seed: int, w: int = 640, h: int = 360) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.uint8)
    hor = int(h * rng.uniform(0.40, 0.48))
    vx = int(w * rng.uniform(0.42, 0.58))

    # trời: gradient
    t = np.linspace(0, 1, hor)[:, None]
    sky = np.stack([235 - 40 * t, 200 - 30 * t, 150 - 20 * t], axis=-1)
    img[:hor] = sky.astype(np.uint8)

    # nhà/cây ở chân trời
    x = 0
    while x < w:
        bw = int(rng.integers(30, 90))
        bh = int(rng.integers(20, int(hor * 0.7)))
        if rng.random() < 0.7:
            c = int(rng.integers(90, 170))
            cv2.rectangle(img, (x, hor - bh), (x + bw, hor), (c, c, c + 5), -1)
            for wy in range(hor - bh + 5, hor - 5, 12):
                for wx in range(x + 5, x + bw - 8, 14):
                    cv2.rectangle(img, (wx, wy), (wx + 6, wy + 6), (c - 50, c - 40, c - 30), -1)
        else:
            cv2.circle(img, (x + bw // 2, hor - bh // 2), bh // 2 + 8, (40, int(rng.integers(90, 140)), 40), -1)
        x += bw + int(rng.integers(0, 20))

    # mặt đất + đường
    img[hor:] = (70, 110, 80)
    road = np.array([[vx - 4, hor], [vx + 4, hor], [w - 20, h], [20, h]])
    cv2.fillPoly(img, [road], (95, 95, 98))
    # vạch kẻ đường (nét đứt giữa, nét liền hai bên)
    for k in range(12):
        y0, y1 = hor + (h - hor) * (k / 12) ** 1.6, hor + (h - hor) * ((k + 0.5) / 12) ** 1.6
        cv2.fillPoly(img, [np.array([[vx - 1 - 6 * (y0 - hor) / (h - hor), y0], [vx + 1 + 6 * (y0 - hor) / (h - hor), y0],
                                     [vx + 1 + 6 * (y1 - hor) / (h - hor), y1], [vx - 1 - 6 * (y1 - hor) / (h - hor), y1]],
                                    np.int32)], (230, 230, 230))
    cv2.line(img, (vx - 3, hor), (28, h), (230, 230, 230), 2)
    cv2.line(img, (vx + 3, hor), (w - 28, h), (230, 230, 230), 2)

    # xe
    for _ in range(int(rng.integers(2, 5))):
        depth = rng.uniform(0.15, 0.75)
        cy = int(hor + (h - hor) * depth)
        cw = int(25 + 110 * depth)
        ch = int(cw * 0.6)
        lane = rng.choice([-0.28, 0.28]) * (w * 0.5) * depth
        cx = int(vx + lane)
        col = tuple(int(v) for v in rng.integers(30, 220, 3))
        cv2.rectangle(img, (cx - cw // 2, cy - ch), (cx + cw // 2, cy), col, -1)
        cv2.rectangle(img, (cx - cw // 3, cy - ch + 3), (cx + cw // 3, cy - ch // 2), (40, 40, 45), -1)
        for sx in (-1, 1):
            cv2.rectangle(img, (cx + sx * cw // 2 - 4, cy - ch // 3), (cx + sx * cw // 2, cy - ch // 3 + 4), (30, 30, 220), -1)

    # texture giống ảnh camera: hạt nhựa đường + nhiễu nhẹ + mềm hoá nhẹ
    f = img.astype(np.float32)
    f[hor:] += rng.normal(0, 7, f[hor:].shape)
    f += rng.normal(0, 2.5, f.shape)
    img = np.clip(f, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(img, (0, 0), 0.6)
