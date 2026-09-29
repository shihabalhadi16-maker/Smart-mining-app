"""محرك MODFLOW باستخدام FloPy"""
import numpy as np
import shutil
from pathlib import Path

try:
    import flopy
    FLOPY_OK = True
except ImportError:
    FLOPY_OK = False


def is_modflow_available():
    if not FLOPY_OK:
        return False, "FloPy غير مثبتة. قم بتثبيتها: pip install flopy"
    try:
        import platform
        exe_names = ["mf6.exe", "mf6"] if platform.system() == "Windows" else ["mf6"]
        for exe in exe_names:
            if shutil.which(exe):
                return True, f"MODFLOW متوفر: {exe}"
        return False, "ملف mf6 التنفيذي غير موجود في PATH"
    except Exception as e:
        return False, f"خطأ: {e}"


def build_and_run_model(workspace, nlay=1, nrow=20, ncol=20,
                        delr=500.0, delc=500.0, top=350.0, botm=50.0,
                        k_value=3.5, recharge_mm=15.0,
                        well_locations=None, well_rates=None,
                        model_name="mining_model"):
    if not FLOPY_OK:
        return {"success": False, "error": "FloPy غير مثبتة"}
    try:
        Path(workspace).mkdir(parents=True, exist_ok=True)

        sim = flopy.mf6.MFSimulation(sim_name="sim", version='mf6',
                                       exe_name="mf6", sim_ws=workspace)
        tdis = flopy.mf6.ModflowTdis(sim, nper=1,
                                       perioddata=[(1.0, 1, 1.0)])
        ims = flopy.mf6.ModflowIms(sim, print_option='SUMMARY',
                                     complexity='SIMPLE',
                                     outer_dvclose=1e-4,
                                     outer_maximum=50, inner_maximum=100)
        gwf = flopy.mf6.ModflowGwf(sim, modelname=model_name,
                                     save_flows=True)
        dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                        delr=delr, delc=delc,
                                        top=top, botm=botm)
        ic = flopy.mf6.ModflowGwfic(gwf, strt=top - 20.0)
        npf = flopy.mf6.ModflowGwfnpf(gwf, icelltype=1, k=k_value,
                                        save_specific_discharge=True)
        sto = flopy.mf6.ModflowGwfsto(gwf, iconvert=1, ss=1e-5, sy=0.15,
                                        steady_state={0: True})
        rech_value = (recharge_mm / 1000.0) / 365.25
        rch = flopy.mf6.ModflowGwfrcha(gwf, recharge=rech_value)

        if well_locations and well_rates:
            wel_data = []
            for i, loc in enumerate(well_locations):
                rate = well_rates[i] if i < len(well_rates) else 0
                wel_data.append((loc, rate))
            wel = flopy.mf6.ModflowGwfwel(gwf,
                stress_period_data={0: wel_data}, print_input=True)

        oc = flopy.mf6.ModflowGwfoc(gwf,
            head_filerecord=f'{model_name}.hds',
            budget_filerecord=f'{model_name}.cbc',
            saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')])

        sim.write_simulation(silent=True)
        success, buff = sim.run_simulation(silent=True)

        if not success:
            return {"success": False, "error": "فشل تشغيل MODFLOW",
                    "buff": str(buff)[:500]}

        head = gwf.output.head().get_data()
        head_2d = head[0, :, :]

        return {"success": True, "heads": head_2d,
                "head_min": float(np.min(head_2d)),
                "head_max": float(np.max(head_2d)),
                "head_mean": float(np.mean(head_2d)),
                "workspace": workspace,
                "nlay": nlay, "nrow": nrow, "ncol": ncol}
    except Exception as e:
        return {"success": False, "error": str(e)}


def estimate_travel_time_modflow(heads, k_value, porosity, delr):
    grad_y, grad_x = np.gradient(heads, delr)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    valid_grad = grad_mag[grad_mag > 1e-6]
    if len(valid_grad) == 0:
        return None
    mean_grad = float(np.mean(valid_grad))
    velocity = (k_value * mean_grad) / porosity
    return {"mean_gradient": round(mean_grad, 6),
            "velocity_m_day": round(velocity, 6),
            "velocity_m_year": round(velocity * 365.25, 3)}
