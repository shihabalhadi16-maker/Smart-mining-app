"""
modflow_engine.py  v61 - generic steady-state MODFLOW 6 box model (FloPy)

IMPORTANT (scientific scope): this is a GENERIC, UNCALIBRATED illustration model:
  * a rectangular unconfined aquifer, uniform K and recharge
  * constant head on all four sides at mid-thickness
  * no observed heads, no site geometry, no calibration
Heads and gradients are therefore a demonstration of the physics, NOT a prediction for a real site.

Fixes vs v56:
  * nlay > 1 used to fail (a scalar botm gave zero-thickness layers): layers are now evenly spaced
  * the 'dry cell' test used -1e20, but MODFLOW writes HDRY = +1e30: now checks >= 1e20 / NaN
  * time and length units are declared (DAYS / METERS)
  * volumetric budget discrepancy is read from the listing file and reported
  * mf6 is called from its path (no copy into every workspace)
  * inputs and well locations are validated before FloPy is called
  * travel-time helper uses correct spacing per axis (delc for rows, delr for columns)
"""
import os
import re
import shutil
import traceback
from pathlib import Path

import numpy as np

try:
    import flopy
    FLOPY_OK = True
except ImportError:
    FLOPY_OK = False

HDRY = 1e20          # any head >= this (MODFLOW HDRY/HNOFLO = 1e30) is dry/inactive
MAX_DISCREPANCY_PCT = 1.0


def is_modflow_available():
    if not FLOPY_OK:
        return False, "FloPy غير مثبتة. قم بتثبيتها: pip install flopy"
    for exe in ("mf6", "mf6.exe"):
        if shutil.which(exe):
            return True, f"MODFLOW متوفر: {exe}"
    return False, "ملف mf6 التنفيذي غير موجود في PATH"


def validate_inputs(nlay, nrow, ncol, delr, delc, top, botm, k_value, recharge_mm,
                    well_locations=None, well_rates=None):
    """Returns an error message, or None if the inputs are acceptable."""
    if int(nlay) < 1:
        return "عدد الطبقات يجب أن يكون ≥ 1"
    if int(nrow) < 3 or int(ncol) < 3:
        return "الشبكة يجب أن تكون 3×3 على الأقل"
    if delr <= 0 or delc <= 0:
        return "أبعاد الخلية يجب أن تكون > 0"
    if botm >= top:
        return f"القاعدة ({botm}) يجب أن تكون أقل من السطح ({top})"
    if (top - botm) < 5:
        return "سمك الخزان صغير جداً (< 5 م)"
    if k_value <= 0:
        return "K يجب أن يكون > 0"
    if recharge_mm < 0:
        return "التغذية لا يمكن أن تكون سالبة"
    if well_locations:
        if not well_rates or len(well_rates) != len(well_locations):
            return "عدد معدلات الضخ يجب أن يساوي عدد الآبار"
        for loc in well_locations:
            lay, row, col = loc
            if not (0 <= lay < nlay and 0 <= row < nrow and 0 <= col < ncol):
                return f"البئر {loc} خارج الشبكة"
    return None


def _boundary_cells(nlay, nrow, ncol):
    cells = set()
    for lay in range(nlay):
        for col in range(ncol):
            cells.add((lay, 0, col)); cells.add((lay, nrow - 1, col))
        for row in range(nrow):
            cells.add((lay, row, 0)); cells.add((lay, row, ncol - 1))
    return sorted(cells)


def _read_discrepancy(workspace, model_name):
    """Last 'PERCENT DISCREPANCY' value in the flow-model listing file (None if not found)."""
    for name in (f"{model_name}.lst", "mfsim.lst"):
        path = os.path.join(workspace, name)
        if os.path.exists(path):
            try:
                with open(path, "r", errors="ignore") as f:
                    vals = re.findall(r"PERCENT DISCREPANCY\s*=\s*([-+0-9.Ee]+)", f.read())
                if vals:
                    return float(vals[-1])
            except Exception:
                pass
    return None


def build_and_run_model(workspace, nlay=1, nrow=20, ncol=20, delr=500.0, delc=500.0,
                        top=350.0, botm=250.0, k_value=3.3, recharge_mm=15.0,
                        well_locations=None, well_rates=None, model_name="mining_model"):
    """Steady-state MODFLOW 6. Units: metres, days. Well rate < 0 = pumping (MODFLOW convention)."""
    if not FLOPY_OK:
        return {"success": False, "error": "FloPy غير مثبتة"}
    err = validate_inputs(nlay, nrow, ncol, delr, delc, top, botm, k_value, recharge_mm,
                          well_locations, well_rates)
    if err:
        return {"success": False, "error": err}
    mf6_exe = shutil.which("mf6") or shutil.which("mf6.exe")
    if not mf6_exe:
        return {"success": False, "error": "ملف mf6 التنفيذي غير موجود في PATH"}
    nlay, nrow, ncol = int(nlay), int(nrow), int(ncol)

    try:
        Path(workspace).mkdir(parents=True, exist_ok=True)
        sim = flopy.mf6.MFSimulation(sim_name="sim", version="mf6", exe_name=mf6_exe, sim_ws=workspace)
        flopy.mf6.ModflowTdis(sim, time_units="DAYS", nper=1, perioddata=[(1.0, 1, 1.0)])
        flopy.mf6.ModflowIms(sim, print_option="SUMMARY", complexity="SIMPLE", outer_dvclose=1e-4,
                             outer_maximum=100, inner_maximum=200, inner_dvclose=1e-5,
                             linear_acceleration="BICGSTAB")
        gwf = flopy.mf6.ModflowGwf(sim, modelname=model_name, save_flows=True)

        botm_layers = [float(v) for v in np.linspace(top, botm, nlay + 1)[1:]]   # evenly spaced layers
        flopy.mf6.ModflowGwfdis(gwf, length_units="METERS", nlay=nlay, nrow=nrow, ncol=ncol,
                                delr=float(delr), delc=float(delc), top=float(top), botm=botm_layers)

        fixed_head = botm + (top - botm) * 0.5
        flopy.mf6.ModflowGwfic(gwf, strt=fixed_head)
        flopy.mf6.ModflowGwfnpf(gwf, icelltype=1, k=float(k_value), save_specific_discharge=True)
        flopy.mf6.ModflowGwfsto(gwf, iconvert=1, ss=1e-5, sy=0.15, steady_state={0: True})
        flopy.mf6.ModflowGwfrcha(gwf, recharge=(recharge_mm / 1000.0) / 365.25)     # m/day

        chd_cells = [(cell, fixed_head) for cell in _boundary_cells(nlay, nrow, ncol)]
        flopy.mf6.ModflowGwfchd(gwf, stress_period_data={0: chd_cells})

        if well_locations:
            flopy.mf6.ModflowGwfwel(gwf, stress_period_data={0: [(tuple(loc), float(r)) for loc, r in zip(well_locations, well_rates)]})

        flopy.mf6.ModflowGwfoc(gwf, head_filerecord=f"{model_name}.hds", budget_filerecord=f"{model_name}.cbc",
                               saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")])
        sim.write_simulation(silent=True)
        files = sorted(os.listdir(workspace))
        ok, buff = sim.run_simulation(silent=True)

        if not ok:
            lst = ""
            path = os.path.join(workspace, "mfsim.lst")
            if os.path.exists(path):
                with open(path, "r", errors="ignore") as f:
                    lst = f.read()[-4000:]
            return {"success": False, "error": "فشل تشغيل MODFLOW", "buff": str(buff)[:2000],
                    "lst_content": lst, "workspace_files": files, "workspace": workspace}

        head = np.array(gwf.output.head().get_data(), dtype=float)       # (nlay, nrow, ncol)
        bad = (~np.isfinite(head)) | (head >= HDRY)
        if bad.any():
            return {"success": False, "error": f"النموذج لم يتقارب أو فيه خلايا جافة ({int(bad.sum())})",
                    "workspace_files": files, "hint": "جرّب زيادة سمك الخزان أو تقليل التغذية"}

        disc = _read_discrepancy(workspace, model_name)
        top_layer = head[0]
        out = {"success": True, "heads": top_layer, "heads_3d": head,
               "head_min": float(top_layer.min()), "head_max": float(top_layer.max()),
               "head_mean": float(top_layer.mean()), "mounding_m": float(top_layer.max() - fixed_head),
               "percent_discrepancy": disc, "workspace": workspace, "workspace_files": files,
               "nlay": nlay, "nrow": nrow, "ncol": ncol, "fixed_head": fixed_head,
               "warnings": ["نموذج عام غير معاير: لا يمثل موقعاً حقيقياً."]}
        if disc is not None and abs(disc) > MAX_DISCREPANCY_PCT:
            out["warnings"].append(f"عدم توازن الحجم {disc}% (> {MAX_DISCREPANCY_PCT}%): النتائج غير موثوقة.")
        return out
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()[-2000:]}


def estimate_travel_time_modflow(heads, k_value, porosity, delr, delc=None, distance_m=None):
    """Mean seepage velocity from the head gradient (v = K i / n). Rows are spaced delc, columns delr."""
    if not (0 < porosity < 1) or k_value <= 0 or delr <= 0:
        return None
    delc = delr if delc is None else delc
    heads = np.asarray(heads, dtype=float)
    grad_y, grad_x = np.gradient(heads, delc, delr)
    mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
    valid = mag[mag > 1e-6]
    if len(valid) == 0:
        return None
    mean_grad = float(np.mean(valid))
    v = k_value * mean_grad / porosity
    out = {"mean_gradient": round(mean_grad, 6), "max_gradient": round(float(valid.max()), 6),
           "velocity_m_day": round(v, 6), "velocity_m_year": round(v * 365.25, 3)}
    if distance_m:
        out["travel_years"] = round(distance_m / v / 365.25, 2)
    return out
