"""
التحقق الإحصائي المتقدم لـ DRASTIC-T
=====================================
- Leave-One-Out Cross-Validation (LOOCV)
- Bootstrap Confidence Intervals
- ROC-AUC Analysis
- Threshold Sensitivity Analysis
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, confusion_matrix, cohen_kappa_score
import matplotlib.pyplot as plt

# ============================================================
# البيانات (من برنامجك)
# ============================================================
data = pd.DataFrame({
    "site": ["Sennar-1", "Sennar-2", "Sennar-3", "Sennar-4", "Sennar-5",
             "Sennar-6", "Sennar-7", "Sennar-8", "Sennar-9", "Sennar-10", "Sennar-11"],
    "DRASTIC": [117, 107, 43, 118, 89, 134, 111, 44, 113, 89, 111],
    "DRASTIC_T": [147, 137, 61, 148, 110, 164, 141, 62, 143, 110, 134],
    "actual": [1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1]  # 1=ملوث، 0=نظيف
})

print("=" * 60)
print("بيانات التحقق (n = 11)")
print("=" * 60)
print(data.to_string(index=False))
print()

# ============================================================
# 1. Kappa الأساسية (بدون Cross-Validation)
# ============================================================
def compute_kappa(y_true, y_pred):
    """حساب Cohen's Kappa"""
    return cohen_kappa_score(y_true, y_pred)

def compute_metrics(y_true, y_pred, threshold):
    """حساب Kappa, Recall, Accuracy"""
    y_pred_binary = (y_pred >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred_binary, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    kappa = compute_kappa(y_true, y_pred_binary)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    
    return {
        "kappa": round(kappa, 3),
        "recall": round(recall * 100, 1),
        "accuracy": round(accuracy * 100, 1),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)
    }

print("=" * 60)
print("1. النتائج الأساسية (بدون Cross-Validation)")
print("=" * 60)

m_drastic = compute_metrics(data["actual"], data["DRASTIC"], 100)
m_drastic_t = compute_metrics(data["actual"], data["DRASTIC_T"], 140)

print(f"\nDRASTIC (عتبة 100):")
print(f"  Kappa = {m_drastic['kappa']}")
print(f"  Recall = {m_drastic['recall']}%")
print(f"  Accuracy = {m_drastic['accuracy']}%")
print(f"  TP={m_drastic['tp']}, TN={m_drastic['tn']}, FP={m_drastic['fp']}, FN={m_drastic['fn']}")

print(f"\nDRASTIC-T (عتبة 140):")
print(f"  Kappa = {m_drastic_t['kappa']}")
print(f"  Recall = {m_drastic_t['recall']}%")
print(f"  Accuracy = {m_drastic_t['accuracy']}%")
print(f"  TP={m_drastic_t['tp']}, TN={m_drastic_t['tn']}, FP={m_drastic_t['fp']}, FN={m_drastic_t['fn']}")

# ============================================================
# 2. Bootstrap Confidence Intervals for Kappa
# ============================================================
print()
print("=" * 60)
print("2. Bootstrap 95% Confidence Intervals (N = 10,000)")
print("=" * 60)

def bootstrap_kappa(y_true, y_pred, threshold, n_boot=10000, seed=42):
    """حساب Bootstrap CI لـ Kappa"""
    np.random.seed(seed)
    n = len(y_true)
    kappas = []
    
    for _ in range(n_boot):
        # Resample with replacement
        idx = np.random.choice(n, size=n, replace=True)
        y_t = y_true[idx]
        y_p = y_pred[idx]
        
        # Skip if all same class
        if len(np.unique(y_t)) < 2:
            continue
        
        y_p_binary = (y_p >= threshold).astype(int)
        
        try:
            k = cohen_kappa_score(y_t, y_p_binary)
            kappas.append(k)
        except:
            continue
    
    kappas = np.array(kappas)
    ci_lower = np.percentile(kappas, 2.5)
    ci_upper = np.percentile(kappas, 97.5)
    
    return {
        "mean": round(np.mean(kappas), 3),
        "std": round(np.std(kappas), 3),
        "ci_95": (round(ci_lower, 3), round(ci_upper, 3)),
        "n_valid": len(kappas)
    }

b_drastic = bootstrap_kappa(data["actual"].values, data["DRASTIC"].values, 100)
b_drastic_t = bootstrap_kappa(data["actual"].values, data["DRASTIC_T"].values, 140)

print(f"\nDRASTIC (عتبة 100):")
print(f"  Mean Kappa = {b_drastic['mean']}")
print(f"  Std = {b_drastic['std']}")
print(f"  95% CI = {b_drastic['ci_95'][0]} to {b_drastic['ci_95'][1]}")

print(f"\nDRASTIC-T (عتبة 140):")
print(f"  Mean Kappa = {b_drastic_t['mean']}")
print(f"  Std = {b_drastic_t['std']}")
print(f"  95% CI = {b_drastic_t['ci_95'][0]} to {b_drastic_t['ci_95'][1]}")

# ============================================================
# 3. Leave-One-Out Cross-Validation (LOOCV)
# ============================================================
print()
print("=" * 60)
print("3. Leave-One-Out Cross-Validation (LOOCV)")
print("=" * 60)

def loocv_analysis(y_true, y_pred, threshold, label):
    """
    LOOCV: في كل تكرار، نترك موقعاً واحداً للاختبار،
    ونحسب Kappa على 10 مواقع.
    """
    n = len(y_true)
    kappas = []
    predictions = []
    
    for i in range(n):
        # Training: كل المواقع ما عدا i
        train_idx = [j for j in range(n) if j != i]
        test_idx = i
        
        y_train = y_true[train_idx]
        y_pred_train = y_pred[train_idx]
        y_test = y_true[test_idx]
        y_pred_test = y_pred[test_idx]
        
        # تحويل إلى binary
        y_train_binary = (y_pred_train >= threshold).astype(int)
        y_test_binary = int(y_pred_test >= threshold)
        
        # حساب Kappa على training
        if len(np.unique(y_train)) >= 2:
            k_train = cohen_kappa_score(y_train, y_train_binary)
            kappas.append(k_train)
        
        # تسجيل التنبؤ للاختبار
        predictions.append({
            "left_out": i,
            "actual": y_test,
            "predicted": y_test_binary,
            "correct": int(y_test == y_test_binary)
        })
    
    kappas = np.array(kappas)
    pred_df = pd.DataFrame(predictions)
    loocv_accuracy = pred_df["correct"].mean() * 100
    
    print(f"\n{label} (عتبة {threshold}):")
    print(f"  Mean Kappa (LOOCV) = {round(np.mean(kappas), 3)}")
    print(f"  Std Kappa = {round(np.std(kappas), 3)}")
    print(f"  LOOCV Accuracy = {round(loocv_accuracy, 1)}%")
    print(f"  عدد التنبؤات الصحيحة = {pred_df['correct'].sum()}/{n}")
    
    return {
        "mean_kappa": round(np.mean(kappas), 3),
        "std_kappa": round(np.std(kappas), 3),
        "loocv_accuracy": round(loocv_accuracy, 1),
        "predictions": pred_df
    }

loocv_drastic = loocv_analysis(
    data["actual"].values, 
    data["DRASTIC"].values, 
    100, 
    "DRASTIC"
)

loocv_drastic_t = loocv_analysis(
    data["actual"].values, 
    data["DRASTIC_T"].values, 
    140, 
    "DRASTIC-T"
)

# ============================================================
# 4. ROC-AUC Analysis
# ============================================================
print()
print("=" * 60)
print("4. ROC-AUC Analysis")
print("=" * 60)

def compute_roc_auc(y_true, scores, label):
    """حساب ROC-AUC"""
    try:
        auc = roc_auc_score(y_true, scores)
        print(f"\n{label}:")
        print(f"  ROC-AUC = {round(auc, 3)}")
        
        if auc >= 0.9:
            interp = "ممتاز (Outstanding)"
        elif auc >= 0.8:
            interp = "جيد جداً (Excellent)"
        elif auc >= 0.7:
            interp = "جيد (Good)"
        elif auc >= 0.6:
            interp = "مقبول (Fair)"
        else:
            interp = "ضعيف (Poor)"
        
        print(f"  التفسير = {interp}")
        return round(auc, 3)
    except Exception as e:
        print(f"  خطأ: {e}")
        return None

auc_drastic = compute_roc_auc(data["actual"].values, data["DRASTIC"].values, "DRASTIC")
auc_drastic_t = compute_roc_auc(data["actual"].values, data["DRASTIC_T"].values, "DRASTIC-T")

# ============================================================
# 5. Threshold Sensitivity Analysis
# ============================================================
print()
print("=" * 60)
print("5. تحليل حساسية العتبة")
print("=" * 60)

def threshold_sweep(y_true, y_pred, thresholds, label):
    """اختبار عدة عتبات"""
    results = []
    for th in thresholds:
        m = compute_metrics(y_true, y_pred, th)
        results.append({
            "threshold": th,
            "kappa": m["kappa"],
            "recall": m["recall"],
            "accuracy": m["accuracy"]
        })
    
    df = pd.DataFrame(results)
    print(f"\n{label}:")
    print(df.to_string(index=False))
    return df

thresholds = [80, 90, 100, 110, 120, 130, 140, 150, 160]

print("\nنتائج DRASTIC:")
drastic_sweep = threshold_sweep(data["actual"].values, data["DRASTIC"].values, thresholds, "DRASTIC")

print("\nنتائج DRASTIC-T:")
drastic_t_sweep = threshold_sweep(data["actual"].values, data["DRASTIC_T"].values, thresholds, "DRASTIC-T")

# ============================================================
# 6. Summary Table
# ============================================================
print()
print("=" * 60)
print("6. جدول ملخص نهائي")
print("=" * 60)

summary = pd.DataFrame({
    "Model": ["DRASTIC", "DRASTIC-T"],
    "Threshold": [100, 140],
    "Kappa (point)": [m_drastic["kappa"], m_drastic_t["kappa"]],
    "Kappa (bootstrap mean)": [b_drastic["mean"], b_drastic_t["mean"]],
    "Kappa 95% CI": [
        f"[{b_drastic['ci_95'][0]}, {b_drastic['ci_95'][1]}]",
        f"[{b_drastic_t['ci_95'][0]}, {b_drastic_t['ci_95'][1]}]"
    ],
    "Kappa (LOOCV)": [loocv_drastic["mean_kappa"], loocv_drastic_t["mean_kappa"]],
    "Recall (%)": [m_drastic["recall"], m_drastic_t["recall"]],
    "Accuracy (%)": [m_drastic["accuracy"], m_drastic_t["accuracy"]],
    "ROC-AUC": [auc_drastic, auc_drastic_t]
})

print()
print(summary.to_string(index=False))

# ============================================================
# 7. حفظ النتائج
# ============================================================
summary.to_csv("statistical_validation_results.csv", index=False, encoding="utf-8-sig")
print("\n✅ تم حفظ النتائج في: statistical_validation_results.csv")
