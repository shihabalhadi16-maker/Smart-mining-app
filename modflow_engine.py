"""محرك MODFLOW 6 - النسخة التشخيصية المتقدمة"""
import numpy as np
import shutil
import os
import subprocess
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
    بناء وتشغيل نموذج MODFLOW 6 مع تشخيص كامل للمشاكل
    """
    if not FLOPY_OK:
        return {"success": False, "error": "FloPy غير مثبتة"}

    try:
        Path(workspace).mkdir(parents=True, exist_ok=True)

        # ===== التحقق من المدخلات =====
        if botm >= top:
            return {"success": False,
                    "error": f"القاعدة ({botm}) يجب أن تكون أقل من السطح ({top})"}
        if top - botm < 5:
            return {"success": False, "error": "سمك الطبقة صغير جداً"}
        if k_value <= 0:
            return {"success": False, "error": "K يجب أن يكون > 0"}
        if recharge_mm < 0:
            return {"success": False, "error": "التغذية لا يمكن أن تكون سالبة"}

        # ===== 0. نسخ mf6 إلى مجلد العمل =====
        mf6_source = shutil.which("mf6")
        mf6_target = os.path.join(workspace, "mf6")
        copy_status = "لم يتم النسخ"

        if mf6_source:
            try:
                if not os.path.exists(mf6_target):
                    shutil.copy2(mf6_source, mf6_target)
                    os.chmod(mf6_target, 0o755)
                    copy_status = f"تم النسخ من {mf6_source} إلى {mf6_target}"
                else:
                    copy_status = "موجود مسبقاً"
            except Exception as e:
                copy_status = f"فشل النسخ: {e}"
        else:
            copy_status = "mf6 غير موجود في PATH"

        # تحديد المسار التنفيذي
        mf6_exe = mf6_target if os.path.exists(mf6_target) else "mf6"

        # ===== 1. المحاكاة =====
        sim = flopy.mf6.MFSimulation(
            sim_name="sim",
            version='mf6',
            exe_name=mf6_exe,
            sim_ws=workspace)

        # ===== 2. الزمن =====
        tdis = flopy.mf6.ModflowTdis(
            sim, nper=1, perioddata=[(1.0, 1, 1.0)])

        # ===== 3. المحلل العددي =====
        ims = flopy.mf6.ModflowIms(
            sim,
            print_option='SUMMARY',
            complexity='SIMPLE',
            outer_dvclose=1e-4,
            outer_maximum=100,
            inner_maximum=200,
            linear_acceleration='BICGSTAB')

        # ===== 4. النموذج =====
        gwf = flopy.mf6.ModflowGwf(
            sim,
            modelname=model_name,
            save_flows=True)

        # ===== 5. الشبكة =====
        dis = flopy.mf6.ModflowGwfdis(
            gwf,
            nlay=nlay, nrow=nrow, ncol=ncol,
            delr=delr, delc=delc,
            top=top,
            botm=botm)

        # ===== 6. الحالة الأولية =====
        strt_value = (top + botm) / 2.0
        ic = flopy.mf6.ModflowGwfic(gwf, strt=strt_value)

        # ===== 7. خصائص التدفق =====
        npf = flopy.mf6.ModflowGwfnpf(
            gwf,
            icelltype=1,
            k=k_value,
            save_specific_discharge=True)

        # ===== 8. التخزين =====
        sto = flopy.mf6.ModflowGwfsto(
            gwf,
            iconvert=1,
            ss=1e-5,
            sy=0.15,
            steady_state={0: True})

        # ===== 9. التغذية =====
        rech_value = (recharge_mm / 1000.0) / 365.25
        rch = flopy.mf6.ModflowGwfrcha(gwf, recharge=rech_value)

        # ===== 10. شرط حدّي ثابت (CHD) =====
        fixed_head = botm + (top - botm) * 0.5
        chd_cells = []
        for col in range(ncol):
            chd_cells.append(((0, 0, col), fixed_head))
            chd_cells.append(((0, nrow - 1, col), fixed_head))
        for row in range(nrow):
            chd_cells.append(((0, row, 0), fixed_head))
            chd_cells.append(((0, row, ncol - 1), fixed_head))
        chd = flopy.mf6.ModflowGwfchd(
            gwf, stress_period_data={0: chd_cells})

        # ===== 11. الآبار =====
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

        # ===== 13. كتابة الملفات =====
        try:
            sim.write_simulation(silent=True)
        except Exception as e:
            return {
                "success": False,
                "error": f"فشل كتابة الملفات: {str(e)}",
                "traceback": str(e),
                "copy_status": copy_status
            }

        # ===== 14. قائمة الملفات المكتوبة =====
        workspace_files = []
        try:
            workspace_files = sorted(os.listdir(workspace))
        except Exception:
            pass

        # ===== 15. قراءة محتوى mfsim.nam =====
        mfsim_content = ""
        mfsim_path = os.path.join(workspace, 'mfsim.nam')
        if os.path.exists(mfsim_path):
            try:
                with open(mfsim_path, 'r') as f:
                    mfsim_content = f.read()
            except Exception as e:
                mfsim_content = f"خطأ في القراءة: {e}"

        # ===== 16. محاولة تشغيل mf6 يدوياً =====
        manual_stdout = ""
        manual_stderr = ""
        manual_code = ""
        manual_status = "لم يتم التشغيل"

        if mf6_source or os.path.exists(mf6_target):
            exe_path = mf6_target if os.path.exists(mf6_target) else mf6_source
            try:
                manual_result = subprocess.run(
                    [exe_path],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=120)
                manual_stdout = (manual_result.stdout or "")[:2000]
                manual_stderr = (manual_result.stderr or "")[:2000]
                manual_code = str(manual_result.returncode)
                manual_status = "تم التشغيل"
            except subprocess.TimeoutExpired:
                manual_status = "انتهت المهلة (120 ثانية)"
            except Exception as e:
                manual_status = f"استثناء: {e}"

        # ===== 17. التشغيل عبر FloPy =====
        try:
            success, buff = sim.run_simulation(silent=True)
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"استثناء أثناء run_simulation: {str(e)}",
                "traceback": traceback.format_exc()[-2000:],
                "workspace_files": workspace_files,
                "mfsim_content": mfsim_content,
                "copy_status": copy_status,
                "manual_status": manual_status,
                "manual_code": manual_code,
                "manual_stdout": manual_stdout,
                "manual_stderr": manual_stderr
            }

        # ===== 18. التحقق من النجاح =====
        if not success:
            # قراءة ملف mfsim.lst
            lst_content = ""
            lst_path = os.path.join(workspace, "mfsim.lst")
            if os.path.exists(lst_path):
                try:
                    with open(lst_path, 'r', errors='ignore') as f:
                        lst_content = f.read()[-4000:]
                except Exception:
                    pass

            return {
                "success": False,
                "error": "فشل تشغيل MODFLOW (Return False)",
                "buff": str(buff)[:2000] if buff else "buff فارغ",
                "workspace_files": workspace_files,
                "mfsim_content": mfsim_content,
                "lst_content": lst_content,
                "copy_status": copy_status,
                "manual_status": manual_status,
                "manual_code": manual_code,
                "manual_stdout": manual_stdout,
                "manual_stderr": manual_stderr,
                "workspace": workspace,
                "hint": "راجع manual_stderr و lst_content و mfsim_content"
            }

        # ===== 19. قراءة النتائج =====
        try:
            head = gwf.output.head().get_data()
            head_2d = head[0, :, :]
        except Exception as e:
            return {
                "success": False,
                "error": f"فشل قراءة النتائج: {str(e)}",
                "workspace_files": workspace_files
            }

        # ===== 20. التحقق من التقارب =====
        if np.any(head_2d < -1e20):
            n_dry = int(np.sum(head_2d < -1e20))
            return {
                "success": False,
                "error": f"النموذج لم يتقارب ({n_dry} خلية جافة)",
                "workspace_files": workspace_files,
                "copy_status": copy_status,
                "hint": "جرّب تقليل K أو زيادة Botm"
            }

        # ===== 21. النجاح =====
        return {
            "success": True,
            "heads": head_2d,
            "head_min": float(np.min(head_2d)),
            "head_max": float(np.max(head_2d)),
            "head_mean": float(np.mean(head_2d)),
            "workspace": workspace,
            "workspace_files": workspace_files,
            "copy_status": copy_status,
            "nlay": nlay, "nrow": nrow, "ncol": ncol,
            "fixed_head": fixed_head,
            "strt_value": strt_value}

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()[-2000:]
        }


def estimate_travel_time_modflow(heads, k_value, porosity, delr):
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
