"""محرك MODFLOW 6 - النسخة المصححة مع شرط حدّي ثابت"""
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
                        delr=500.0, delc=500.0, top=350.0, botm=250.0,
                        k_value=3.3, recharge_mm=15.0,
                        well_locations=None, well_rates=None,
                        model_name="mining_model"):
    """
    بناء وتشغيل نموذج MODFLOW 6 مع شرط حدّي ثابت (CHD)
    
    ملاحظات مهمة:
    - botm يجب أن يكون أقل من top
    - تمت إضافة CHD على الحدود لضمان التقارب
    - منسوب البداية = منتصف الطبقة
    """
    if not FLOPY_OK:
        return {"success": False, "error": "FloPy غير مثبتة"}

    try:
        Path(workspace).mkdir(parents=True, exist_ok=True)

        # ===== التحقق من المدخلات =====
        if botm >= top:
            return {"success": False,
                    "error": f"منسوب القاعدة ({botm}) يجب أن يكون أقل من السطح ({top})"}
        if top - botm < 5:
            return {"success": False,
                    "error": "سمك الطبقة صغير جداً (يجب > 5 م)"}
        if k_value <= 0:
            return {"success": False, "error": "K يجب أن يكون > 0"}
        if recharge_mm < 0:
            return {"success": False, "error": "التغذية لا يمكن أن تكون سالبة"}

        # ===== 1. المحاكاة =====
        sim = flopy.mf6.MFSimulation(
            sim_name="sim",
            version='mf6',
            exe_name="mf6",
            sim_ws=workspace)

        # ===== 2. الزمن =====
        tdis = flopy.mf6.ModflowTdis(
            sim, nper=1, perioddata=[(1.0, 1, 1.0)])

        # ===== 3. المحلل العددي =====
        ims = flopy.mf6.ModflowIms(
            sim,
            print_option='SUMMARY',
            complexity='MODERATE',
            outer_dvclose=1e-5,
            outer_maximum=200,
            inner_maximum=300,
            linear_acceleration='BICGSTAB',
            relaxation_factor=0.97)

        # ===== 4. النموذج =====
        gwf = flopy.mf6.ModflowGwf(
            sim,
            modelname=model_name,
            save_flows=True,
            newtonoptions="NEWTON UNDER_RELAXATION")

        # ===== 5. الشبكة =====
        dis = flopy.mf6.ModflowGwfdis(
            gwf,
            nlay=nlay, nrow=nrow, ncol=ncol,
            delr=delr, delc=delc,
            top=top,
            botm=botm)

        # ===== 6. الحالة الأولية =====
        # منسوب البداية = منتصف الطبقة
        strt_value = (top + botm) / 2.0
        ic = flopy.mf6.ModflowGwfic(gwf, strt=strt_value)

        # ===== 7. خصائص التدفق (NPF) =====
        npf = flopy.mf6.ModflowGwfnpf(
            gwf,
            icelltype=1,  # convertible: يمكن أن تصبح الخلايا جافة
            k=k_value,
            save_specific_discharge=True)

        # ===== 8. التخزين =====
        sto = flopy.mf6.ModflowGwfsto(
            gwf,
            iconvert=1,
            ss=1e-5,
            sy=0.15,
            steady_state={0: True})

        # ===== 9. التغذية (Recharge) =====
        rech_value = (recharge_mm / 1000.0) / 365.25
        rch = flopy.mf6.ModflowGwfrcha(gwf, recharge=rech_value)

        # ===== 10. شرط حدّي ثابت (CHD) على الحدود =====
        # هذا ضروري لتصريف المياه وضمان التقارب
        fixed_head = botm + (top - botm) * 0.5  # منتصف الطبقة
        chd_cells = []

        # الحد العلوي والسفلي
        for col in range(ncol):
            chd_cells.append(((0, 0, col), fixed_head))
            chd_cells.append(((0, nrow - 1, col), fixed_head))

        # الحد الأيسر والأيمن
        for row in range(nrow):
            chd_cells.append(((0, row, 0), fixed_head))
            chd_cells.append(((0, row, ncol - 1), fixed_head))

        chd = flopy.mf6.ModflowGwfchd(
            gwf, stress_period_data={0: chd_cells})

        # ===== 11. الآبار (WEL) =====
        if well_locations and well_rates:
            wel_data = []
            for i, loc in enumerate(well_locations):
                rate = well_rates[i] if i < len(well_rates) else 0
                wel_data.append((loc, rate))
            wel = flopy.mf6.ModflowGwfwel(
                gwf, stress_period_data={0: wel_data}, print_input=True)

        # ===== 12. المخرجات =====
        oc = flopy.mf6.ModflowGwfoc(
            gwf,
            head_filerecord=f'{model_name}.hds',
            budget_filerecord=f'{model_name}.cbc',
            saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')])

        # ===== 13. الكتابة والتشغيل =====
        sim.write_simulation(silent=True)
        success, buff = sim.run_simulation(silent=True)

        if not success:
            return {"success": False,
                    "error": "فشل تشغيل MODFLOW",
                    "buff": str(buff)[-2000:]}

        # ===== 14. قراءة النتائج =====
        head = gwf.output.head().get_data()
        head_2d = head[0, :, :]  # الطبقة الأولى

        # ===== 15. التحقق من التقارب =====
        if np.any(head_2d < -1e20):
            n_dry = int(np.sum(head_2d < -1e20))
            return {"success": False,
                    "error": f"النموذج لم يتقارب ({n_dry} خلية جافة). "
                             f"جرّب: تقليل K، أو زيادة Botm، أو زيادة التغذية"}

        # ===== 16. إحصائيات =====
        return {
            "success": True,
            "heads": head_2d,
            "head_min": float(np.min(head_2d)),
            "head_max": float(np.max(head_2d)),
            "head_mean": float(np.mean(head_2d)),
            "workspace": workspace,
            "nlay": nlay, "nrow": nrow, "ncol": ncol,
            "fixed_head": fixed_head,
            "strt_value": strt_value}

    except Exception as e:
        import traceback
        return {"success": False, "error": str(e),
                "traceback": traceback.format_exc()[-1500:]}


def estimate_travel_time_modflow(heads, k_value, porosity, delr):
    """تقدير زمن الوصول باستخدام التدرج الهيدروليكي المحسوب"""
    grad_y, grad_x = np.gradient(heads, delr)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    valid_grad = grad_mag[grad_mag > 1e-6]
    if len(valid_grad) == 0:
        return None
    mean_grad = float(np.mean(valid_grad))
    velocity = (k_value * mean_grad) / porosity
    return {
        "mean_gradient": round(mean_grad, 6),
        "velocity_m_day": round(velocity, 6),
        "velocity_m_year": round(velocity * 365.25, 3)}
