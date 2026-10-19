"""اختبارات الوحدة على طبقات اصطناعية معروفة النتيجة (ليست بيانات ميدانية)."""
import sys, importlib.util, numpy as np
sys.path.insert(0, "/home/claude"); sys.path.insert(0, "/home/claude/stubs")
import gis_overlay as G
spec = importlib.util.spec_from_file_location("app", "/home/claude/app.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
A.install_core_shim()
res = []
def chk(name, ok, detail=""):
    res.append((name, bool(ok), str(detail)))

# 1) constant layers -> constant index equal to the point calculator (manual site: 72)
shape = (3, 4)
const_site = {"depth_m": 15, "recharge_mm": 20, "slope_pct": 3, "conductivity": 3,
              "aquifer": "massive_shale", "soil": "thin_or_absent", "vadose": "confining_layer"}
rat = {"D": G.reclassify(np.full(shape, 15.0), A.r_D), "R": G.reclassify(np.full(shape, 20.0), A.r_R),
       "T": G.reclassify(np.full(shape, 3.0), A.r_T), "C": G.reclassify(np.full(shape, 3.0), A.r_C),
       "A": G.reclassify_categorical(np.full(shape, "massive_shale", dtype=object), A.AQUIFER),
       "S": G.reclassify_categorical(np.full(shape, "thin_or_absent", dtype=object), A.SOIL),
       "I": G.reclassify_categorical(np.full(shape, "confining_layer", dtype=object), A.VADOSE)}
idx = G.weighted_overlay(rat)
chk("constant layers reproduce point calculator (72)", np.allclose(idx, A.index_of(A.ratings(const_site))), idx[0, 0])

# 2) random grid: every cell equals point calculator on the same cell values
rng = np.random.default_rng(5)
D = rng.uniform(2, 60, (6, 6)); R = rng.uniform(5, 300, (6, 6)); T = rng.uniform(0, 15, (6, 6)); C = np.exp(rng.uniform(np.log(0.05), np.log(100), (6, 6)))
AQ = np.array([[list(A.AQUIFER)[int(v)] for v in row] for row in rng.integers(0, len(A.AQUIFER), (6, 6))], dtype=object)
SO = np.array([[list(A.SOIL)[int(v)] for v in row] for row in rng.integers(0, len(A.SOIL), (6, 6))], dtype=object)
VA = np.array([[list(A.VADOSE)[int(v)] for v in row] for row in rng.integers(0, len(A.VADOSE), (6, 6))], dtype=object)
rat = {"D": G.reclassify(D, A.r_D), "R": G.reclassify(R, A.r_R), "T": G.reclassify(T, A.r_T), "C": G.reclassify(C, A.r_C),
       "A": G.reclassify_categorical(AQ, A.AQUIFER), "S": G.reclassify_categorical(SO, A.SOIL), "I": G.reclassify_categorical(VA, A.VADOSE)}
grid = G.weighted_overlay(rat)
worst = 0
for i in range(6):
    for j in range(6):
        pt = {"depth_m": D[i, j], "recharge_mm": R[i, j], "slope_pct": T[i, j], "conductivity": C[i, j],
              "aquifer": AQ[i, j], "soil": SO[i, j], "vadose": VA[i, j]}
        worst = max(worst, abs(grid[i, j] - A.index_of(A.ratings(pt))))
chk("36 random cells match the point calculator exactly", worst == 0, f"max diff={worst}")

# 3) monotonicity: deeper water -> lower or equal index (rating does not increase with depth)
base = np.full(shape, 15.0); deeper = np.full(shape, 40.0)
r1 = G.reclassify(base, A.r_D); r2 = G.reclassify(deeper, A.r_D)
chk("deeper water never increases the depth rating", np.all(r2 <= r1), (r1[0, 0], r2[0, 0]))

# 4) NaN is not silently filled
D_nan = D.copy(); D_nan[2, 2] = np.nan
rat_nan = dict(rat); rat_nan["D"] = G.reclassify(D_nan, A.r_D)
g_nan = G.weighted_overlay(rat_nan)
chk("NaN in one layer propagates to that cell only", np.isnan(g_nan[2, 2]) and np.sum(np.isnan(g_nan)) == 1, np.sum(np.isnan(g_nan)))

# 5) unknown category raises, not defaults
try:
    G.reclassify_categorical(np.array([["unknown_rock"]], dtype=object), A.AQUIFER); ok5 = False
except ValueError:
    ok5 = True
chk("unknown category raises ValueError", ok5)

# 6) shape mismatch and missing layer raise
try:
    G.weighted_overlay({**rat, "D": np.zeros((2, 2))}); ok6a = False
except ValueError:
    ok6a = True
try:
    G.weighted_overlay({k: v for k, v in rat.items() if k != "C"}); ok6b = False
except ValueError:
    ok6b = True
chk("shape mismatch raises", ok6a); chk("missing layer raises", ok6b)

# 7) classification threshold is the stated 140 and keeps NaN
cl = G.classify(np.array([[139.9, 140.0, np.nan]]))
chk("classify uses >=140 and keeps NaN", cl[0, 0] == 0 and cl[0, 1] == 1 and np.isnan(cl[0, 2]), cl)

# 8) top cells ignore NaN and are sorted descending
tc = G.top_cells(grid, k=3)
chk("top cells sorted descending", all(tc[i][2] >= tc[i + 1][2] for i in range(len(tc) - 1)), tc)

# 9) weights sum (DRASTIC total weight) = 23
chk("total weight = 23 (so index range is 23..226 with ratings 1..10)", sum(G.W_STD.values()) == 23)

for n, ok, d in res:
    print(("PASS" if ok else "FAIL"), n, d)
print(f"{sum(o for _, o, _ in res)}/{len(res)} passed")
