"""T1 - Sức khoẻ camera ADAS: baseline vs 5 loại lỗi x 4 mức.
Chạy:  python src/run_benchmark.py            (dùng data/images/* nếu có, ngược lại cảnh tổng hợp)
       python src/run_benchmark.py --n 12 --seed 0
Đầu ra trong results/: metrics.csv, summary.csv, flags_old.csv, flags.csv, flags_compare.csv,
latency.csv, trend.png, before_after.png, run.log"""
import argparse, glob, os, platform, sys, time
import cv2, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from degrade import DEGRADATIONS
from make_scene import make_scene
from metrics import METRIC_FNS, compute, gray

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
METRICS = list(METRIC_FNS)
SAT_THR = 0.05          # luật chói: >5% pixel gần trắng (ngưỡng đặt tay, chưa hiệu chuẩn)
NOISE_K = 2.0           # luật nhiễu mới: noise_sigma > NOISE_K x median baseline (đặt trước khi chạy)
RAIN_K = 2.0            # luật mưa mới: streak_ratio > RAIN_K x median baseline và KHÔNG có cờ nhiễu
FLAG_COLS = ["flag_blur", "flag_dark", "flag_glare", "flag_noise", "flag_rain", "flag_any"]
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
        summ[f"d_{m}_%"] = (summ[m] / base[m] - 1) * 100 if base[m] != 0 else np.nan  # baseline 0 -> không tính %
    order = ["baseline"] + list(DEGRADATIONS)
    summ["o"] = summ.cond.map(order.index)
    summ = summ.sort_values(["o", "level"]).drop(columns="o")
    summ.to_csv(os.path.join(OUT, "summary.csv"), index=False)
    pd.set_option("display.width", 200, "display.max_columns", 30, "display.float_format", "{:.4g}".format)
    log("\n== Trung bình theo điều kiện (so với baseline) ==")
    log(summ[["cond", "level", "param"] + METRICS + ["d_blur_score_%", "d_blur_norm_%", "d_noise_sigma_%", "d_streak_ratio_%"]].to_string(index=False))

    order_map = {c: k for k, c in enumerate(order)}

    def rate(d, cols):
        r = d.groupby(["cond", "level", "param"], as_index=False)[cols].mean()
        r["o"] = r.cond.map(order_map)
        return r.sort_values(["o", "level"]).drop(columns="o")

    # ---- LUẬT CŨ (giữ nguyên để so sánh): ngưỡng hiệu chuẩn trên toàn bộ baseline (in-sample)
    b_all = df[df.cond == "baseline"]
    blur_thr = 0.5 * b_all.blur_score.median()
    dark_thr = 0.5 * b_all.mean_gray.median()
    old = df.copy()
    old["flag_blur"] = old.blur_score < blur_thr
    old["flag_dark"] = old.mean_gray < dark_thr
    old["flag_glare"] = old.sat_ratio > SAT_THR
    old["flag_any"] = old[["flag_blur", "flag_dark", "flag_glare"]].any(axis=1)
    flags_old = rate(old, ["flag_blur", "flag_dark", "flag_glare", "flag_any"])
    flags_old.to_csv(os.path.join(OUT, "flags_old.csv"), index=False)
    log(f"\n== LUẬT CŨ (tỷ lệ frame bị gắn cờ, mọi ảnh, in-sample). Ngưỡng: blur_score < {blur_thr:.1f}; "
        f"mean_gray < {dark_thr:.1f}; sat_ratio > {SAT_THR} ==")
    log(flags_old.to_string(index=False))

    # ---- LUẬT MỚI: hiệu chuẩn trên nửa đầu ảnh (calib), báo cáo trên nửa sau (test) -> không in-sample
    n_cal = len(imgs) // 2
    cal_base = df[(df.cond == "baseline") & (df.img < n_cal)]
    bn_thr = 0.5 * cal_base.blur_norm.median()
    dark_thr2 = 0.5 * cal_base.mean_gray.median()
    noise_thr = NOISE_K * cal_base.noise_sigma.median()
    rain_thr = RAIN_K * cal_base.streak_ratio.median()
    new = df.copy()
    new["flag_blur"] = new.blur_norm < bn_thr
    new["flag_dark"] = new.mean_gray < dark_thr2
    new["flag_glare"] = new.sat_ratio > SAT_THR
    new["flag_noise"] = new.noise_sigma > noise_thr
    new["flag_rain"] = (new.streak_ratio > rain_thr) & ~new.flag_noise
    new["flag_any"] = new[FLAG_COLS[:5]].any(axis=1)
    test = new[new.img >= n_cal]
    flags = rate(test, FLAG_COLS)
    flags.to_csv(os.path.join(OUT, "flags.csv"), index=False)
    log(f"\n== LUẬT MỚI (tỷ lệ cờ trên ảnh TEST {n_cal}..{len(imgs) - 1}; ngưỡng hiệu chuẩn trên baseline ảnh "
        f"0..{n_cal - 1}). Ngưỡng: blur_norm < {bn_thr:.4g}; mean_gray < {dark_thr2:.1f}; sat_ratio > {SAT_THR}; "
        f"noise_sigma > {noise_thr:.2f} (= {NOISE_K} x median {cal_base.noise_sigma.median():.2f}); "
        f"streak_ratio > {rain_thr:.4f} (= {RAIN_K} x median) và không có cờ nhiễu ==")
    log(flags.to_string(index=False))

    # ---- so sánh cũ vs mới trên CÙNG ảnh test (luật cũ vẫn dùng ngưỡng cũ)
    cmp_ = rate(old[old.img >= n_cal], ["flag_blur", "flag_any"]).rename(
        columns={"flag_blur": "old_blur", "flag_any": "old_any"})
    cmp_ = cmp_.merge(flags[["cond", "level", "flag_blur", "flag_noise", "flag_rain", "flag_any"]].rename(
        columns={"flag_blur": "new_blur", "flag_noise": "new_noise", "flag_rain": "new_rain", "flag_any": "new_any"}),
        on=["cond", "level"])
    cmp_.to_csv(os.path.join(OUT, "flags_compare.csv"), index=False)
    log("\n== So sánh tỷ lệ cờ cũ vs mới trên ảnh test ==")
    log(cmp_.to_string(index=False))

    # ---- latency từng metric (ms/frame, CPU, đo trên ảnh baseline, lặp 20 lần)
    lat = []
    for m, fn in METRIC_FNS.items():
        ts = []
        for im in imgs:
            g = gray(im)
            fn(g)  # warm-up
            t0 = time.perf_counter()
            for _ in range(20):
                fn(g)
            ts.append((time.perf_counter() - t0) / 20 * 1000)
        lat.append({"metric": m, "ms_per_frame_mean": np.mean(ts), "ms_per_frame_max": np.max(ts)})
    lat = pd.DataFrame(lat)
    lat.to_csv(os.path.join(OUT, "latency.csv"), index=False)
    log(f"\n== Latency (ms/frame, ảnh {imgs[0].shape[1]}x{imgs[0].shape[0]}, CPU {platform.processor() or platform.machine()}) ==")
    log(lat.to_string(index=False))

    # ---- plot xu hướng: hàng = metric, cột = loại lỗi
    fig, axs = plt.subplots(len(METRICS), len(DEGRADATIONS), figsize=(18, 16), sharex="col")
    for c, (name, (_, params, unit)) in enumerate(DEGRADATIONS.items()):
        for r, m in enumerate(METRICS):
            ax = axs[r, c]
            g = df[df.cond.isin(["baseline", name])].groupby("level")[m]
            mu, sd = g.mean(), g.std()
            ax.errorbar(mu.index, mu.values, yerr=sd.values, marker="o", capsize=3)
            ax.axhline(base[m], ls="--", c="gray", lw=0.8)
            if m in ("blur_score", "blur_norm"):
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

    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
