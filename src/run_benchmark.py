"""T1 - Sức khoẻ camera ADAS: baseline vs 5 loại lỗi x 4 mức.
Chạy:  python src/run_benchmark.py            (dùng data/images/* nếu có, ngược lại cảnh tổng hợp)
       python src/run_benchmark.py --n 12 --seed 0
Đầu ra trong results/: metrics.csv, summary.csv, flags.csv, trend.png, before_after.png, run.log"""
import argparse, glob, os, platform, sys
import cv2, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from degrade import DEGRADATIONS
from make_scene import make_scene
from metrics import compute

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
METRICS = ["blur_score", "sat_ratio", "entropy", "mean_gray", "orb_kp"]
SAT_THR = 0.05          # luật chói: >5% pixel gần trắng (ngưỡng đặt tay, chưa hiệu chuẩn)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def load_images(n, seed, data_dir, width=0):
    files = sorted(sum([glob.glob(os.path.join(data_dir, e)) for e in ("*.jpg", "*.jpeg", "*.png")], []))
    if files:
        imgs = []
        for f in files[:n]:
            im = cv2.imread(f)
            h, w = im.shape[:2]
            if width and w != width:
                im = cv2.resize(im, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)
            imgs.append(im)
        return imgs, f"ảnh thật trong {data_dir} ({len(imgs)} ảnh, {imgs[0].shape[1]}x{imgs[0].shape[0]} px, {'resize' if width else 'giữ nguyên độ phân giải'})"
    return [make_scene(seed + i) for i in range(n)], f"cảnh đường TỔNG HỢP (make_scene, seed {seed}..{seed + n - 1})"


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "images"), help="thư mục ảnh thật (nếu rỗng thì dùng cảnh tổng hợp)")
    ap.add_argument("--width", type=int, default=0, help="resize ảnh thật về chiều rộng này (0 = giữ nguyên)")
    ap.add_argument("--out", default=OUT, help="thư mục ghi kết quả")
    args = ap.parse_args()
    OUT = args.out
    os.makedirs(OUT, exist_ok=True)

    imgs, src = load_images(args.n, args.seed, args.data, args.width)
    log(f"Nguồn dữ liệu: {src}")
    log(f"python {platform.python_version()}, opencv {cv2.__version__}, numpy {np.__version__}, seed={args.seed}")

    rows = []
    for i, im in enumerate(imgs):
        rows.append({"img": i, "cond": "baseline", "level": 0, "param": 0.0, **compute(im)})
        for name, (fn, params, _) in DEGRADATIONS.items():
            for lv, p in enumerate(params, 1):
                rng = np.random.default_rng(args.seed * 1000 + i * 100 + lv)  # lặp lại được
                rows.append({"img": i, "cond": name, "level": lv, "param": p, **compute(fn(im, p, rng))})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "metrics.csv"), index=False)

    # ---- bảng tóm tắt: trung bình theo (điều kiện, mức) + chênh lệch so với baseline
    base = df[df.cond == "baseline"][METRICS].mean()
    summ = df.groupby(["cond", "level", "param"], as_index=False)[METRICS].mean()
    for m in METRICS:
        summ[f"d_{m}_%"] = (summ[m] / base[m] - 1) * 100
    order = ["baseline"] + list(DEGRADATIONS)
    summ["o"] = summ.cond.map(order.index)
    summ = summ.sort_values(["o", "level"]).drop(columns="o")
    summ.to_csv(os.path.join(OUT, "summary.csv"), index=False)
    pd.set_option("display.width", 200, "display.max_columns", 30, "display.float_format", "{:.4g}".format)
    log("\n== Trung bình theo điều kiện (so với baseline) ==")
    log(summ[["cond", "level", "param"] + METRICS + ["d_blur_score_%", "d_orb_kp_%"]].to_string(index=False))

    # ---- luật sức khoẻ camera: hiệu chuẩn ngưỡng trên baseline (in-sample, xem limitation)
    blur_thr = 0.5 * df[df.cond == "baseline"].blur_score.median()
    dark_thr = 0.5 * df[df.cond == "baseline"].mean_gray.median()
    df["flag_blur"] = df.blur_score < blur_thr
    df["flag_dark"] = df.mean_gray < dark_thr
    df["flag_glare"] = df.sat_ratio > SAT_THR
    df["flag_any"] = df[["flag_blur", "flag_dark", "flag_glare"]].any(axis=1)
    flags = df.groupby(["cond", "level", "param"], as_index=False)[["flag_blur", "flag_dark", "flag_glare", "flag_any"]].mean()
    flags["o"] = flags.cond.map(order.index)
    flags = flags.sort_values(["o", "level"]).drop(columns="o")
    flags.to_csv(os.path.join(OUT, "flags.csv"), index=False)
    log(f"\n== Luật cờ (tỷ lệ frame bị gắn cờ). Ngưỡng: blur_score < {blur_thr:.1f}; mean_gray < {dark_thr:.1f}; sat_ratio > {SAT_THR} ==")
    log(flags.to_string(index=False))

    # ---- plot xu hướng: hàng = metric, cột = loại lỗi
    fig, axs = plt.subplots(len(METRICS), len(DEGRADATIONS), figsize=(18, 11), sharex="col")
    for c, (name, (_, params, unit)) in enumerate(DEGRADATIONS.items()):
        for r, m in enumerate(METRICS):
            ax = axs[r, c]
            g = df[df.cond.isin(["baseline", name])].groupby("level")[m]
            mu, sd = g.mean(), g.std()
            ax.errorbar(mu.index, mu.values, yerr=sd.values, marker="o", capsize=3)
            ax.axhline(base[m], ls="--", c="gray", lw=0.8)
            if m == "blur_score":
                ax.set_yscale("log")
            if c == 0:
                ax.set_ylabel(m)
            if r == 0:
                ax.set_title(name)
            if r == len(METRICS) - 1:
                ax.set_xticks(range(5))
                ax.set_xticklabels(["base"] + [str(p) for p in params])
                ax.set_xlabel(unit)
    fig.suptitle("T1: metric theo mức lỗi (đường đứt = baseline; thanh = độ lệch chuẩn giữa các ảnh)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "trend.png"), dpi=110)
    plt.close(fig)

    # ---- ảnh trước/sau cho ảnh đầu tiên
    fig, axs = plt.subplots(len(DEGRADATIONS), 5, figsize=(16, 9))
    for r, (name, (fn, params, unit)) in enumerate(DEGRADATIONS.items()):
        for c in range(5):
            if c == 0:
                im, t = imgs[0], "baseline"
            else:
                im = fn(imgs[0], params[c - 1], np.random.default_rng(1))
                t = f"{name} {params[c - 1]}"
            axs[r, c].imshow(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
            axs[r, c].set_title(t, fontsize=9)
            axs[r, c].axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "before_after.png"), dpi=90)
    plt.close(fig)

    with open(os.path.join(OUT, "run.log"), "w") as f:
        f.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
