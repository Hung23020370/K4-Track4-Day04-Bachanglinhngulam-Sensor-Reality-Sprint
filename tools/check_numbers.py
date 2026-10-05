"""In các con số mà notes/failure_case.md trích dẫn, lấy từ results/*.csv, để đối chiếu sau khi chạy lại.
Dùng:  python tools/check_numbers.py [thư_mục_results]"""
import os, sys, pandas as pd

d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "results")
s = pd.read_csv(os.path.join(d, "summary.csv")); f = pd.read_csv(os.path.join(d, "flags.csv"))
b = s[s.cond == "baseline"].iloc[0]
print(f"baseline: blur_score={b.blur_score:.1f}  orb_kp={b.orb_kp:.0f}  entropy={b.entropy:.2f}  mean_gray={b.mean_gray:.1f}")
for c, lv in [("noise", 1), ("noise", 2), ("noise", 3), ("noise", 4), ("rain", 4), ("night", 1), ("glare", 1), ("glare", 4)]:
    r = s[(s.cond == c) & (s.level == lv)].iloc[0]; g = f[(f.cond == c) & (f.level == lv)].iloc[0]
    print(f"{c:5s} {r.param:>6g}: blur={r.blur_score:9.1f} ({r.blur_score / b.blur_score:6.1f}x)  orb={r.orb_kp:6.0f}  entropy={r.entropy:.2f}  "
          f"mean_gray={r.mean_gray:6.1f}  cờ: blur={g.flag_blur:.2f} tối={g.flag_dark:.2f} chói={g.flag_glare:.2f} any={g.flag_any:.2f}")
print("baseline bị cờ any:", f[f.cond == 'baseline'].iloc[0].flag_any)
