# 📖 DRASTIC-Tox — User Guide

> **دليل المستخدم الشامل لمنصة DRASTIC-Tox**
> **Comprehensive User Guide for the DRASTIC-Tox Platform**

**Version 58.6** | **University of Khartoum — Faculty of Engineering**

---

## 📑 Table of Contents / فهرس المحتويات

### 🇸🇦 القسم العربي
1. [مقدمة](#-مقدمة)
2. [البدء السريع](#-البدء-السريع)
3. [واجهة التطبيق](#-واجهة-التطبيق)
4. [شرح التبويبات](#-شرح-التبويبات)
5. [أوضاع التشغيل](#-أوضاع-التشغيل)
6. [تحضير البيانات](#-تحضير-البيانات)
7. [تفسير النتائج](#-تفسير-النتائج)
8. [حل المشاكل](#-حل-المشاكل)
9. [الأسئلة الشائعة](#-الأسئلة-الشائعة)

### 🇬🇧 English Section
10. [Introduction](#-introduction)
11. [Quick Start](#-quick-start)
12. [Interface Overview](#-interface-overview)
13. [Tabs Guide](#-tabs-guide)
14. [Operating Modes](#-operating-modes)
15. [Data Preparation](#-data-preparation)
16. [Interpreting Results](#-interpreting-results)
17. [Troubleshooting](#-troubleshooting)
18. [FAQ](#-faq)

---

# 🇸🇦 القسم العربي

## 🎯 مقدمة

**DRASTIC-Tox** هي منصة ويب لتقييم مخاطر تلوث المياه الجوفية في مناطق التعدين الأهلي والصناعي في السودان. تعتمد المنصة على نموذج **DRASTIC** الكلاسيكي، مع إضافة مؤشرات السمية (CN و Hg) للحصول على نموذج محسّن هو **DRASTIC-Tox**.

### 🎯 الأهداف
- تقييم سريع لمخاطر التلوث لأي موقع
- مقارنة المواقع المختلفة
- اقتراح حلول عملية
- دعم اتخاذ القرار

### ⚠️ تنبيه مهم
**DRASTIC-Tox أداة فرز أولي (Screening Tool)** — لا تُغني عن:
- التحليل المخبري للمياه
- الفحص الميداني
- استشارة مهندس هيدروجيولوجي مؤهل

---

## 🚀 البدء السريع

### الخطوة 1: افتح التطبيق
اذهب إلى: `smart-mining-app.streamlit.app`

### الخطوة 2: اختر اللغة
- من الشريط الجانبي، اختر **🇸🇦 العربية** أو **🇬🇧 English**

### الخطوة 3: اختر النمط
- من **نطاق البيانات**، اختر:
  - **⛏️ تقليدي** — لتعدين الذهب الأهلي
  - **🏭 صناعي** — للمناجم الصناعية
  - **🌍 الكل** — لعرض الجميع

### الخطوة 4: اختر موقعاً
- اذهب إلى تبويب **📍 المدخلات**
- اختر **الولاية** ثم **الموقع**
- ستظهر جميع المؤشرات والحسابات فوراً

### الخطوة 5: راجع النتائج
- **DRASTIC Index**: 117/230 (متوسط)
- **DRASTIC-Tox Index**: 154.9/280 (مرتفع)
- **التوصية**: إجراء عاجل

---

## 🖥️ واجهة التطبيق

### البنية العامة

```
┌─────────────────────────────────────────────────┐
│  🌐 اللغة | 📤 الرفع | ⚙️ النمط | 📊 الحالة      │  ← الشريط الجانبي
├─────────────────────────────────────────────────┤
│  ⛏️ نظام التعدين السوداني v58.6                  │  ← الترويسة
│  DRASTIC + DRASTIC-Tox + MODFLOW 6              │
├─────────────────────────────────────────────────┤
│  📤 منطقة رفع الملفات + 🔍 فحص البيانات          │  ← منطقة الرفع
├─────────────────────────────────────────────────┤
│  📍 المدخلات | ➕ يدوي | 📊 جماعي | ... | 🔬    │  ← 17 تبويب
├─────────────────────────────────────────────────┤
│                                                  │
│              محتوى التبويب المختار               │
│                                                  │
└─────────────────────────────────────────────────┘
```

### الشريط الجانبي

| العنصر | الوظيفة |
|--------|---------|
| **اللغة** | تبديل عربي/إنجليزي فوري |
| **رفع الملفات** | 3 خانات: تحقق، جماعي، إضافي |
| **جودة البيانات** | عدد المواقع الموثقة والعرض فقط |
| **النمط** | تقليدي / صناعي / الكل |
| **الوضع** | 8 أوضاع تشغيل مختلفة |
| **الحالة** | حالة MODFLOW والمؤشر الحالي |
| **حول** | معلومات الإصدار والوحدات |

---

## 📑 شرح التبويبات

### 📍 تبويب 1: المدخلات (Inputs)

**الوظيفة:** اختيار موقع وتقييمه.

**الاستخدام:**
1. اختر **الولاية** (18 ولاية متاحة)
2. اختر **الموقع** من القائمة
3. ستظهر:
   - **معلومات الموقع**: النشاط، الموسم، التوثيق
   - **المعايير السبعة**: العمق، التغذية، الميل، إلخ
   - **قيم التلوث**: CN و Hg
   - **DRASTIC Index**: النتيجة الأساسية
   - **DRASTIC-Tox Index**: النتيجة المعدّلة
   - **زر تحميل التقرير HTML**

**مثال:**
```
الموقع: Ghaat_Haffer_Dry
DRASTIC: 117/230 → متوسط
DRASTIC-Tox: 154.9/280 → مرتفع
التوصية: إجراء عاجل
```

---

### ➕ تبويب 2: الإدخال اليدوي (Manual Entry)

**الوظيفة:** إضافة موقع جديد غير موجود في القاعدة.

**الاستخدام:**
1. أدخل بيانات الموقع الجديد:
   - الولاية والاسم
   - الإحداثيات (خط الطول والعرض)
   - المعايير السبعة (D, R, A, S, T, I, C)
   - قيم CN و Hg
   - حالة التلوث الفعلي
2. اضغط **💾 حفظ**
3. سيُضاف الموقع للقائمة الدائمة

⚠️ **ملاحظة:** الموقع الجديد يُحفظ في الجلسة الحالية فقط.

---

### 📊 تبويب 3: التقييم الجماعي (Bulk Assessment)

**الوظيفة:** تقييم قائمة كاملة من المواقع من ملف Excel/CSV.

**الاستخدام:**
1. ارفع ملف CSV/Excel من الشريط الجانبي
2. عدّل **العتبات**:
   - DRASTIC: 100 (افتراضي)
   - DRASTIC-Tox: 106.5 (افتراضي)
3. ستظهر:
   - جدول بالمواقع المصنفة (HIGH/LOW)
   - **Kappa** للمقارنة
   - **Recall** للنموذجين
4. حمّل النتائج بـ CSV

---

### 🛡️ تبويب 4: الحلول (Solutions)

**الوظيفة:** حساب أثر الحلول المقترحة.

**الحلول المتاحة:**
- **بطانة HDPE** — تخفيض 60%
- **معالجة السيانيد** — تخفيض 40%
- **آبار مراقبة** — تخفيض 15%

**الاستخدام:**
1. اختر حلّاً أو أكثر
2. سيُحسب:
   - المؤشر قبل
   - المؤشر بعد
   - نسبة التخفيض

**مثال:**
```
قبل: 117
بعد: 23.9
التخفيض: 79.6%
```

---

### 📄 تبويب 5: التقرير (Report)

**الوظيفة:** عرض ملخص كامل + تصدير PDF و Excel.

**المحتوى:**
- جدول DRASTIC, DRASTIC-Tox
- تفاصيل Bonus (CN, Hg, SF)
- المستوى (Level) والإجراء (Action)

**زران:**
- **📄 تحميل PDF** — تقرير احترافي (إنجليزي)
- **📊 تحميل Excel** — تقرير بـ 5 أوراق

---

### 🗺️ تبويب 6: الخريطة الحرارية (Heatmap)

**الوظيفة:** عرض جميع المواقع الموثقة على خريطة تفاعلية.

**خيارات العرض:**
- **كلاهما** — علامات + طبقة حرارية
- **علامات** — نقاط فقط
- **حراري** — طبقة حرارية فقط

**التحكم:**
- **الارتفاع**: من 400 إلى 900 بكسل

**الإحصاءات:**
- منخفض / متوسط / مرتفع / مرتفع جداً

---

### 📈 تبويب 7: الحساسية (Sensitivity)

**الوظيفة:** تحليل SPSA (Single Parameter Sensitivity Analysis).

**التبويبات الفرعية:**

#### SPSA
- يقارن الوزن الفعلي بالوزن النظري
- يحدد **أكثر معيار مؤثر** في الموقع
- المرجع: Napolitano & Fabbri (1996)

**مثال:**
```
الأكثر تأثيراً: I (Vadose Zone) — +12.45%
الأقل تأثيراً: R (Recharge) — -13.97%
```

#### Variation
- يختبر تأثير تغيير قيمة كل معيار على المؤشر
- يحدد **حساسية** كل معيار

---

### ☠️ تبويب 8: السمية (Toxicity)

**الوظيفة:** تحليل مفصّل لمؤشر السمية.

**المدخلات:**
- Hg في التربة (mg/kg)
- CN في التربة (mg/kg)

**المخرجات:**
- **DRASTIC-Tox Bonus** — يُستخدم في التقرير
- **Toxicity Index** — مع عامل التربة الإضافي
- **معامل التربة (Soil Factor)**
- **التصنيف**: آمن / تحت المراقبة / خطير / حرج
- **الإجراء**: لا إجراء / دوري / عاجل / إيقاف النشاط

---

### 🌍 تبويب 9: GIS

**الوظيفة:** عرض وتنزيل بيانات جميع المواقع.

**الفلاتر:**
- **الكل** — 40 موقعاً
- **الموثقة فقط** — 11 موقعاً
- **للعرض فقط** — 29 موقعاً

**التنزيل:** ملف CSV بـ UTF-8 ليدعم العربية.

---

### 🎲 تبويب 10: Monte Carlo

**الوظيفة:** محاكاة عدم اليقين.

**المدخلات:**
- **عدد المحاكاات**: 100–5000 (افتراضي 1000)
- **نسبة التغيير**: 5–30% (افتراضي 15%)

**المخرجات:**
- **DRASTIC**: Mean, Std, CI 90%, P>140
- **DRASTIC-Tox**: Mean, Std, CI 90%, P>140, P>180, Range

**مثال على الفرز السريع:**
```
DRASTIC:      Mean=116.9, P>140 = 0.0%
DRASTIC-Tox: Mean=153.5, P>140 = 98.8%
```

---

### 🔬 تبويب 11: التحقق المتقدم

**الوظيفة:** حساب Kappa, ROC-AUC, Bootstrap, LOOCV.

**المتطلبات:**
- ملف تحقق بأعمدة `actual_contaminated`

**المخرجات:**
- **Kappa** — 0.0 إلى 1.0
- **ROC-AUC** — 0.5 إلى 1.0
- **F1-Score**
- **Bootstrap CI** (1000 عينة)
- **LOOCV** — Leave-One-Out Cross-Validation

---

### 🚀 تبويب 12: تطوير النموذج

**الوظيفة:** مقارنة نماذج وحساب أوزان AHP.

**التبويبات الفرعية:**
- **المنطقة الرمادية** — مواقع غير مؤكدة
- **معايرة α, β** — يدوياً
- **مقارنة النماذج** — DRASTIC vs AHP-DRASTIC vs DRASTIC-Tox

---

### 🗺️ تبويب 13: الخرائط التلقائية

**الوظيفة:** توليد خرائط Plotly احترافية.

**المخرجات:**
- خريطة Plotly تفاعلية
- إمكانية التنزيل كـ HTML

---

### 🎯 تبويب 14: معايرة الأوزان

**الوظيفة:** إيجاد أفضل α, β, SF تلقائياً.

**المدخلات:**
- **نمط التعدين**: تقليدي/صناعي/مختلط
- **دقة البحث**: 10–30 خطوة
- **عتبة DRASTIC-Tox**: افتراضي 140

**المخرجات:**
- أفضل Kappa
- أفضل α, β, SF
- أفضل 10 تركيبات

---

### 📐 تبويب 15: العتبة المثلى

**الوظيفة:** إيجاد العتبة المثلى باستخدام Youden Index.

**المخرجات:**
- **Optimal Threshold** (مثلاً 128)
- **Youden J**
- **Sensitivity** و **Specificity**
- **ROC Curve** تفاعلية

---

### ⚙️ تبويب 16: Weight Profiles Manager

**الوظيفة:** إدارة أوزان محفوظة.

**الأوزان المتاحة:**
- Literature (من الأدبيات)
- Calibrated (معايَرة)

**الاستخدام:**
1. اختر النمط (تقليدي/صناعي/مختلط)
2. راجع الأوزان المتاحة
3. اضغط **Activate** للتفعيل

---

### 🔬 تبويب 17: التحقق الخارجي (External Validation)

**الوظيفة:** تحقق حقيقي باستخدام Train/Test + K-Fold CV.

**الخطوات:**
1. ارفع ملف التحقق
2. اختر:
   - **Mining Type**
   - **Test Size %**: 20–50 (افتراضي 30)
   - **K-Folds**: 3–10 (افتراضي 5)
   - **Thresholds**
3. اضغط **🚀 Run External Validation**

**المخرجات:**

| Metric | DRASTIC | DRASTIC-Tox |
|--------|---------|-------------|
| Kappa | 0.0 | **1.0** |
| ROC-AUC | 0.0 | **1.0** |
| CV Kappa | 0.0 | **0.75** |
| PR-AUC | 0.583 | **1.0** |
| Brier | 0.295 | **0.246** |

**Baseline ML:**
- DRASTIC-Tox (fixed threshold)
- Logistic Regression
- Random Forest

---

## 🎮 أوضاع التشغيل

المنصة تعمل بـ **8 أوضاع**:

| # | الوضع | الوظيفة |
|---|-------|---------|
| 1 | 🏠 **النظام الأساسي** | 17 تبويب كاملة |
| 2 | 🌾 **القطاع الزراعي** | SAR + Na% + EC |
| 3 | ✅ **التحقق الفعلي** | مقارنة النموذج بالواقع |
| 4 | 🚀 **نقل الملوثات** | محاكاة Advection-Dispersion |
| 5 | 🔬 **التحقق المستقل** | Split يدوي |
| 6 | 🛰️ **الأقمار الصناعية** | NASA POWER API |
| 7 | ⏳ **الديناميكي** | تغير المخاطر عبر الزمن |
| 8 | 🌊 **MODFLOW** | محاكاة فيزيائية كاملة |

---

## 📊 تحضير البيانات

### الصيغة المطلوبة (CSV / Excel)

| العمود | النوع | الحدود |
|-------|-------|--------|
| `depth_m` | رقم | 0.1 – 500 |
| `recharge_mm` | رقم | 0 – 2000 |
| `slope_pct` | رقم | 0 – 90 |
| `conductivity` | رقم | 0.001 – 1000 |
| `aquifer` | نص | انظر القيم |
| `soil` | نص | انظر القيم |
| `vadose` | نص | انظر القيم |
| `cn_water_mg_l` | رقم | 0 – 100 |
| `hg_water_mg_l` | رقم | 0 – 50 |
| `actual_contaminated` | 0 أو 1 | — |

### القيم المقبولة

**Aquifer:**
```
massive_shale, metamorphic_igneous,
weathered_metamorphic_igneous,
thin_bedded_sequences, massive_sandstone,
massive_limestone, sand_and_gravel,
basalt, karst_limestone
```

**Soil:**
```
thin_or_absent, gravel, sand, peat,
shrinking_aggregated_clay, sandy_loam,
loam, silty_loam, clay_loam, muck,
nonshrinking_clay
```

**Vadose:**
```
confining_layer, silt_clay, shale,
metamorphic_igneous, limestone, sandstone,
sand_gravel_silt_clay, sand_gravel,
basalt, karst_limestone
```

### التحقق من الملف

بعد الرفع، اضغط **🔍 فحص الملف** في قسم الرفع. ستحصل على:
- **درجة الجودة** (0–100)
- **أخطاء حرجة** (إن وُجدت)
- **تحذيرات**
- **ملاحظات**

---

## 🔍 تفسير النتائج

### تفسير DRASTIC-Tox Index

| المدى | المستوى | الإجراء |
|-------|---------|---------|
| 23 – 100 | 🟢 منخفض | روتيني |
| 100 – 140 | 🟡 متوسط | مراقبة دورية |
| 140 – 180 | 🟠 مرتفع | إجراء عاجل |
| 180 – 280 | 🔴 مرتفع جداً | إجراء فوري |

### تفسير Kappa

| القيمة | التفسير |
|--------|---------|
| 0.0 – 0.20 | ضعيف |
| 0.21 – 0.40 | مقبول |
| 0.41 – 0.60 | متوسط |
| 0.61 – 0.80 | جيد |
| 0.81 – 1.00 | ممتاز |

### تفسير ROC-AUC

| القيمة | التفسير |
|--------|---------|
| 0.5 | عشوائي |
| 0.7 – 0.8 | مقبول |
| 0.8 – 0.9 | ممتاز |
| 0.9 – 1.0 | مثالي |

---

## 🔧 حل المشاكل

### المشكلة: التطبيق لا يعمل
**الحل:**
1. أعد تحميل الصفحة (Ctrl+Shift+R)
2. امسح الكاش
3. جرب متصفحاً آخر
4. تحقق من الإنترنت

### المشكلة: خطأ في رفع ملف
**الحل:**
1. استخدم الزر **🔍 فحص الملف** لمعرفة السبب
2. تأكد من الصيغة (CSV UTF-8 أو Excel)
3. تحقق من الأعمدة المطلوبة

### المشكلة: PDF لا يُنتج
**الحل:**
- النص العربي يُترجم تلقائياً للإنجليزية
- تحقق من وجود بيانات الموقع

### المشكلة: Excel لا يُنتج
**الحل:**
- تأكد من وجود ملف `excel_exporter.py`
- تحقق من About → excel_exporter: OK

### المشكلة: Kappa = 0
**الحل:**
- العتبة قد تكون غير مناسبة
- استخدم تبويب **📐 العتبة المثلى**
- جرّب عتبة جديدة

---

## ❓ الأسئلة الشائعة

### س: هل DRASTIC-Tox بديل عن التحليل المخبري؟
**ج:** لا. هي أداة فرز أولي فقط.

### س: كم موقعاً يمكنني إدخاله؟
**ج:** حتى 1000 موقع (يُنصح بـ 20–50 للدقة).

### س: هل يمكنني تعديل الأوزان؟
**ج:** نعم، من تبويب **🎯 معايرة الأوزان**.

### س: ما الفرق بين DRASTIC و DRASTIC-Tox؟
**ج:** DRASTIC يقيس قابلية التلوث، DRASTIC-Tox يضيف السمية.

### س: هل البيانات آمنة؟
**ج:** نعم، البيانات محلية في الجلسة فقط.

### س: كيف أستشهد بالمنصة؟
**ج:**
```bibtex
@software{dangal2026drastic,
  title = {DRASTIC-Tox: Modified DRASTIC Model for Sudan},
  author = {Dangal, Shihab Alhadi and Ali, Sarah Akasha},
  year = {2026},
  version = {v58.6}
}
```

---

# 🇬🇧 English Section

## 🎯 Introduction

**DRASTIC-Tox** is a web-based platform for assessing groundwater contamination risk in artisanal and industrial mining regions of Sudan. It extends the classical **DRASTIC** model with cyanide (CN) and mercury (Hg) toxicity indicators.

### ⚠️ Important Disclaimer
DRASTIC-Tox is a **screening tool** — it does NOT replace:
- Laboratory water analysis
- Field investigation
- Consultation with qualified hydrogeologists

---

## 🚀 Quick Start

### Step 1: Open the App
Navigate to: `smart-mining-app.streamlit.app`

### Step 2: Choose Language
From the sidebar, select **🇬🇧 English**.

### Step 3: Choose Pattern
From **Data Scope**, select:
- **⛏️ Traditional** — Artisanal gold mining
- **🏭 Industrial** — Industrial mines
- **🌍 All** — Show all

### Step 4: Select Site
Go to **📍 Inputs** tab, choose **State** → **Site**.

### Step 5: Review Results
- **DRASTIC Index**: 117/230 (Medium)
- **DRASTIC-Tox Index**: 154.9/280 (High)
- **Action**: Urgent

---

## 🖥️ Interface Overview

### Sidebar Controls

| Element | Function |
|---------|----------|
| **Language** | AR/EN switch |
| **Upload Files** | 3 slots: validation, bulk, extra |
| **Data Quality** | Verified vs display counts |
| **Scope** | Traditional / Industrial / All |
| **Mode** | 8 operating modes |
| **Status** | MODFLOW + current index |
| **About** | Version info + modules |

---

## 📑 Tabs Guide

### 📍 Tab 1: Inputs
- Select state and site
- View 7 parameters + CN/Hg
- See DRASTIC and DRASTIC-Tox indices
- Download HTML report

### ➕ Tab 2: Manual Entry
- Add new site with custom data
- Saves to session only

### 📊 Tab 3: Bulk Assessment
- Upload CSV/Excel file
- Set thresholds
- Get Kappa + Recall for both models
- Download results

### 🛡️ Tab 4: Solutions
- HDPE liner (60% reduction)
- Cyanide treatment (40%)
- Monitoring wells (15%)
- Calculate combined impact

### 📄 Tab 5: Report
- Summary of all metrics
- **📄 Download PDF** (English report)
- **📊 Download Excel** (5 sheets)

### 🗺️ Tab 6: Heatmap
- Folium interactive map
- View modes: Both / Markers / Heat

### 📈 Tab 7: Sensitivity
- **SPSA**: Compare theoretical vs effective weights
- **Variation**: Test parameter sensitivity

### ☠️ Tab 8: Toxicity
- Detailed toxicity analysis
- Two metrics: DRASTIC-Tox Bonus, Toxicity Index

### 🌍 Tab 9: GIS
- View all 40 sites
- Filter: All / Verified / Display-only
- Download CSV

### 🎲 Tab 10: Monte Carlo
- 100–5000 iterations
- Outputs: Mean, Std, CI 90%, P>140

### 🔬 Tab 11: Advanced Validation
- Kappa, ROC-AUC, F1, Bootstrap CI, LOOCV

### 🚀 Tab 12: Model Development
- Gray zone analysis
- α, β calibration
- Model comparison

### 🗺️ Tab 13: Auto Maps
- Plotly interactive maps
- HTML export

### 🎯 Tab 14: Weight Calibration
- Auto-find best α, β, SF
- Top 10 combinations

### 📐 Tab 15: Optimal Threshold
- Youden Index method
- ROC Curve
- Sensitivity + Specificity

### ⚙️ Tab 16: Weight Profiles
- Literature vs Calibrated profiles
- One-click activation

### 🔬 Tab 17: External Validation
- Train/Test split (70/30)
- Stratified K-Fold CV
- Baseline ML (LogReg, Random Forest)
- Enhanced metrics (PR-AUC, Brier)

---

## 🎮 Operating Modes

| # | Mode | Function |
|---|------|----------|
| 1 | 🏠 **Core System** | 17 tabs |
| 2 | 🌾 **Agricultural** | SAR + Na% + EC |
| 3 | ✅ **Verification** | Ground truth validation |
| 4 | 🚀 **Transport** | Advection-Dispersion |
| 5 | 🔬 **Independent** | Manual split |
| 6 | 🛰️ **Satellite** | NASA POWER API |
| 7 | ⏳ **Dynamic** | Temporal risk |
| 8 | 🌊 **MODFLOW** | Physical simulation |

---

## 📊 Data Preparation

### Required Columns

| Column | Type | Range |
|--------|------|-------|
| `depth_m` | Number | 0.1 – 500 |
| `recharge_mm` | Number | 0 – 2000 |
| `slope_pct` | Number | 0 – 90 |
| `conductivity` | Number | 0.001 – 1000 |
| `aquifer` | Text | See values |
| `soil` | Text | See values |
| `vadose` | Text | See values |
| `cn_water_mg_l` | Number | 0 – 100 |
| `hg_water_mg_l` | Number | 0 – 50 |
| `actual_contaminated` | 0 or 1 | — |

### Validation

After upload, click **🔍 Validate File** to get:
- **Quality score** (0–100)
- **Critical errors**
- **Warnings**
- **Info notes**

---

## 🔍 Interpreting Results

### DRASTIC-Tox Index

| Range | Level | Action |
|-------|-------|--------|
| 23 – 100 | 🟢 Low | Routine |
| 100 – 140 | 🟡 Medium | Periodic |
| 140 – 180 | 🟠 High | Urgent |
| 180 – 280 | 🔴 Very High | Immediate |

### Kappa Interpretation (Landis & Koch, 1977)

| Value | Interpretation |
|-------|----------------|
| 0.0 – 0.20 | Slight |
| 0.21 – 0.40 | Fair |
| 0.41 – 0.60 | Moderate |
| 0.61 – 0.80 | Substantial |
| 0.81 – 1.00 | Almost Perfect |

---

## 🔧 Troubleshooting

### App not loading
1. Hard refresh (Ctrl+Shift+R)
2. Clear cache
3. Try another browser

### File upload error
1. Click **🔍 Validate File** to see reason
2. Ensure CSV UTF-8 or Excel format
3. Check required columns

### PDF not generating
- Arabic text is auto-translated to English
- Ensure site data exists

### Excel not generating
- Verify `excel_exporter.py` exists
- Check About → excel_exporter: OK

### Kappa = 0
- Threshold may be wrong
- Use **📐 Optimal Threshold** tab

---

## ❓ FAQ

### Q: Is DRASTIC-Tox a substitute for lab testing?
**A:** No. It's a screening tool only.

### Q: How many sites can I add?
**A:** Up to 1000 sites (20–50 recommended).

### Q: Can I modify weights?
**A:** Yes, from **🎯 Weight Calibration** tab.

### Q: What's the difference between DRASTIC and DRASTIC-Tox?
**A:** DRASTIC measures vulnerability; DRASTIC-Tox adds toxicity.

### Q: Is data safe?
**A:** Yes, data is session-local only.

### Q: How to cite?
```bibtex
@software{dangal2026drastic,
  title = {DRASTIC-Tox: Modified DRASTIC Model for Sudan},
  author = {Dangal, Shihab Alhadi and Ali, Sarah Akasha},
  year = {2026},
  version = {v58.6}
}
```

---

## 📞 Support / الدعم

| Channel / القناة | Contact / التواصل |
|------------------|-------------------|
| **Email / البريد** | Shihabalhadi16@gmail.com |
| **GitHub Issues** | [smart-mining-app/issues](https://github.com/shihabahadi16-maker/smart-mining-app/issues) |
| **Location / الموقع** | Singa, Al-Salam — Sennar State, Sudan |

---

## 📚 References / المراجع

1. **Aller et al. (1987)** — DRASTIC: US EPA
2. **Napolitano & Fabbri (1996)** — SPSA
3. **Konaté et al. (2025)** — Modified DRASTIC
4. **Landis & Koch (1977)** — Kappa
5. **Youden (1950)** — Optimal threshold
6. **WHO (2022)** — Water quality guidelines

---

<div align="center">

**DRASTIC-Tox v58.6** | **University of Khartoum** | **2026**

**Built with ❤️ for Sudan's groundwater protection**

</div>
