"""
drastic_core.py - standards-based core (pure Python, no dependencies)

References
  DRASTIC & Pesticide DRASTIC : Aller et al. (1987) EPA/600/2-87/035
  Drinking-water limits        : EU Directive 98/83/EC; WHO GDWQ 4th ed.+addenda
  Irrigation water             : Richards (1954) USDA HB 60; Ayers & Westcot (1985) FAO 29
  Crop salt tolerance          : Maas & Hoffman (1977) / FAO 29 Table 4  (VERIFY values)

Design rules
  1. Vulnerability (DRASTIC) and contamination hazard are kept SEPARATE.
  2. Unknown categories raise errors (no silent defaults).
  3. Hazard uses ONE log scale for all contaminants, scores 0 if <= limit.
  4. Everything is documented as screening-level, not a regulatory tool.
"""
import math
from bisect import bisect_left

# ---------------------------------------------------------------- weights
W_STD = dict(D=5, R=4, A=3, S=2, T=1, I=5, C=3)    # DRASTIC      range 23-226
W_PEST = dict(D=5, R=4, A=3, S=5, T=3, I=4, C=2)   # Pesticide    range 26-256

# ---------------------------------------------------------------- ratings
def _bin(x, edges, ratings, name):
    if x is None or x < 0:
        raise ValueError(f"{name}: invalid value {x}")
    return ratings[bisect_left(edges, x)]          # x <= edge -> that bin

def rate_D(m):  return _bin(m, [1.5, 4.6, 9.1, 15.2, 22.9, 30.5], [10, 9, 7, 5, 3, 2, 1], "D")
def rate_R(mm): return _bin(mm, [50.8, 101.6, 177.8, 254.0], [1, 3, 6, 8, 9], "R")
def rate_T(pct): return _bin(pct, [2, 6, 12, 18], [10, 9, 5, 3, 1], "T")
def rate_C(md): return _bin(md, [4.074, 12.222, 28.518, 40.74, 81.48], [1, 2, 4, 6, 8, 10], "C")

AQUIFER = {"massive_shale": 2, "metamorphic_igneous": 3, "weathered_metamorphic_igneous": 4,
           "glacial_till": 5, "thin_bedded_sequences": 6, "massive_sandstone": 6,
           "massive_limestone": 6, "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10}
SOIL = {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8, "shrinking_aggregated_clay": 7,
        "sandy_loam": 6, "loam": 5, "silty_loam": 4, "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1}
VADOSE = {"confining_layer": 1, "silt_clay": 3, "shale": 3, "metamorphic_igneous": 4,
          "limestone": 6, "sandstone": 6, "bedded_limestone_sandstone": 6,
          "sand_gravel_silt_clay": 6, "sand_gravel": 8, "basalt": 9, "karst_limestone": 10}

def _cat(table, key, name):
    if key not in table:
        raise ValueError(f"{name}: unknown category '{key}'. Valid: {sorted(table)}")
    return table[key]

def ratings(site):
    return dict(D=rate_D(site["depth_m"]), R=rate_R(site["recharge_mm"]),
                A=_cat(AQUIFER, site["aquifer"], "A"), S=_cat(SOIL, site["soil"], "S"),
                T=rate_T(site["slope_pct"]), I=_cat(VADOSE, site["vadose"], "I"),
                C=rate_C(site["conductivity_m_d"]))

def index(site, weights=W_STD):
    r = ratings(site)
    return sum(r[k] * w for k, w in weights.items())

def index_range(weights):
    mx = dict(D=10, R=9, A=10, S=10, T=10, I=10, C=10)
    return sum(weights.values()), sum(mx[k] * w for k, w in weights.items())

def vulnerability_class(idx, weights=W_STD):
    """Relative classes on normalised 0-100 scale (convention, NOT part of Aller 1987)."""
    lo, hi = index_range(weights)
    p = (idx - lo) / (hi - lo) * 100
    return ("low" if p < 25 else "moderate" if p < 50 else "high" if p < 75 else "very_high"), round(p, 1)

# ---------------------------------------------------------------- hazard
LIMITS_MG_L = {"EU":  {"cn": 0.05, "hg": 0.001},    # Directive 98/83/EC
               "WHO": {"cn": None, "hg": 0.006}}    # WHO cyanide GV withdrawn (2009)

def check_units(cn=None, hg=None):
    w = []
    if hg is not None and hg > 0.1:
        w.append(f"Hg={hg} mg/L is >100x typical ASGM water values; check ug/L vs mg/L.")
    if cn is not None and cn > 5:
        w.append(f"CN={cn} mg/L is very high; check units.")
    return w

def hazard_quotient(conc, limit):
    if limit is None:
        raise ValueError("No limit defined for this standard/contaminant")
    return conc / limit

def hazard_score(conc, limit, hq_ref=1000.0, max_score=30.0):
    """0 if compliant; log10 scale; saturates only at HQ >= hq_ref (assumption)."""
    hq = hazard_quotient(conc, limit)
    if hq <= 1:
        return 0.0
    return min(max_score, max_score * math.log10(hq) / math.log10(hq_ref))

def hazard_class(max_hq):
    return ("compliant" if max_hq <= 1 else "elevated" if max_hq <= 10
            else "high" if max_hq <= 100 else "severe")

def experimental_tox(idx, cn, hg, standard="EU", w_cn=1.0, w_hg=1.0, hq_ref=1000.0):
    """EXPERIMENTAL DRASTIC-Tox: idx + min(50, w_cn*s_cn + w_hg*s_hg). Range 23-276.
    Weights are an unvalidated assumption -> run sensitivity analysis."""
    L = LIMITS_MG_L[standard]
    s_cn = hazard_score(cn, L["cn"], hq_ref) if L["cn"] else 0.0
    s_hg = hazard_score(hg, L["hg"], hq_ref)
    return idx + min(50.0, w_cn * s_cn + w_hg * s_hg), s_cn, s_hg

_MATRIX = {"low": ["low", "low", "moderate", "moderate"],
           "moderate": ["low", "moderate", "moderate", "high"],
           "high": ["moderate", "moderate", "high", "high"],
           "very_high": ["moderate", "high", "high", "very_high"]}
_HZ = ["compliant", "elevated", "high", "severe"]

def risk_category(vuln_cls, haz_cls):
    """Two-axis screening matrix (preferred over adding concentrations to DRASTIC)."""
    return _MATRIX[vuln_cls][_HZ.index(haz_cls)]

# ---------------------------------------------------------------- irrigation
def sar(na, ca, mg):                               # meq/L
    return na / math.sqrt((ca + mg) / 2.0)

def na_percent(na, k, ca, mg):                     # meq/L
    return (na + k) / (ca + mg + na + k) * 100.0

def ussl_salinity(ec):                             # dS/m
    return "C1" if ec < 0.25 else "C2" if ec < 0.75 else "C3" if ec < 2.25 else "C4"

def ussl_sodium(s):
    return "S1" if s <= 10 else "S2" if s <= 18 else "S3" if s <= 26 else "S4"

def fao_salinity_hazard(ecw):
    return "none" if ecw < 0.7 else "slight_moderate" if ecw <= 3.0 else "severe"

_INF = [(3, 0.7, 0.2), (6, 1.2, 0.3), (12, 1.9, 0.5), (20, 2.9, 1.3), (40, 5.0, 2.9)]
def fao_infiltration_hazard(s, ecw):
    """FAO 29 Table 1: reduced infiltration from SAR + ECw."""
    for smax, hi, lo in _INF:
        if s <= smax:
            return "none" if ecw > hi else "slight_moderate" if ecw >= lo else "severe"
    return "severe"

CROPS = {  # (ECe threshold dS/m, slope %/dS/m)  -- VERIFY against FAO 29 Table 4
    "wheat": (6.0, 7.1), "maize": (1.7, 12.0), "sorghum": (6.8, 16.0),
    "cotton": (7.7, 5.2), "sugarcane": (1.7, 5.9), "groundnut": (3.2, 29.0)}

def relative_yield(crop, ecw, leaching_factor=1.5):
    """Maas-Hoffman: Yr = 100 - b(ECe - a);  ECe ~ 1.5*ECw (15-20% leaching)."""
    a, b = CROPS[crop]
    ece = leaching_factor * ecw
    return round(100.0 if ece <= a else max(0.0, 100.0 - b * (ece - a)), 1)

# ---------------------------------------------------------------- self-test
def _selftest():
    assert index_range(W_STD) == (23, 226), index_range(W_STD)
    assert index_range(W_PEST) == (26, 256), index_range(W_PEST)
    assert VADOSE["silt_clay"] == 3
    site = dict(depth_m=3, recharge_mm=120, aquifer="sand_and_gravel", soil="sandy_loam",
                slope_pct=1, vadose="sand_gravel", conductivity_m_d=30)
    # D9*5 + R6*4 + A8*3 + S6*2 + T10*1 + I8*5 + C6*3 = 45+24+24+12+10+40+18
    assert index(site) == 173, index(site)
    assert hazard_score(0.05, 0.05) == 0 and hazard_score(0.001, 0.001) == 0
    assert round(sar(10, 4, 2), 2) == 5.77
    assert relative_yield("wheat", 1.0) == 100.0
    assert experimental_tox(100, 0.0, 0.0)[0] == 100
    try:
        rate_D(-1); raise SystemExit("negative depth not rejected")
    except ValueError:
        pass
    print("all self-tests passed")

if __name__ == "__main__":
    _selftest()
