"""
auto_maps.py — توليد خرائط تلقائية من بيانات DRASTIC-Tox
=========================================================
يولّد 12 خريطة في لوحة واحدة (Multi-Panel):
- D, R, A, S, T, I, C (المعايير السبعة)
- CN, Hg (الملوثات)
- DRASTIC, DRASTIC-Tox (المؤشرات)
- التصنيف النهائي

المكتبات المطلوبة:
    plotly>=5.0
    scipy>=1.10
    numpy>=1.20
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import griddata


MAX_KM = 50.0  # أقصى مسافة من أي موقع مُقاس يُسمح بالاستيفاء عندها


def _km_distance_to_nearest(xi, yi, x, y):
    """المسافة بالكيلومتر من كل نقطة شبكة إلى أقرب موقع مُقاس (تقريب كروي مقبول لهذا النطاق)."""
    gx = xi.ravel(); gy = yi.ravel()
    dy = (gy[:, None] - y[None, :]) * 111.0
    dx = (gx[:, None] - x[None, :]) * 111.0 * np.cos(np.radians(gy))[:, None]
    return np.sqrt(dx ** 2 + dy ** 2).min(axis=1).reshape(xi.shape)


def _interpolate_idw(x, y, z, xi, yi, power=2.0):
    """
    Interpolation using Inverse Distance Weighting (IDW).
    Fallback to scipy griddata if too few points.
    """
    points = np.column_stack([x, y])
    grid_points = np.column_stack([xi.ravel(), yi.ravel()])

    try:
        # linear داخل حدود البيانات فقط. لا تُملأ الأماكن الفارغة بأقرب نقطة.
        if len(points) >= 4:
            zi = griddata(points, z, grid_points, method='linear')
        else:
            zi = griddata(points, z, grid_points, method='nearest')
    except Exception:
        # Fallback: IDW
        dist = np.sqrt((grid_points[:, 0:1] - points[:, 0][None, :])**2 +
                       (grid_points[:, 1:2] - points[:, 1][None, :])**2)
        dist = np.where(dist < 1e-10, 1e-10, dist)
        weights = 1.0 / (dist ** power)
        zi = (weights * z[None, :]).sum(axis=1) / weights.sum(axis=1)

    zi = zi.reshape(xi.shape)
    # إخفاء أي شبكة تبعد أكثر من MAX_KM عن أقرب موقع مُقاس
    zi = np.where(_km_distance_to_nearest(xi, yi, x, y) > MAX_KM, np.nan, zi)
    return zi


def _make_map_plot(df, value_col, title, colorscale, unit=""):
    """إنشاء لوحة خريطة واحدة"""
    x = df["lon"].values
    y = df["lat"].values
    z = df[value_col].values

    if len(x) < 3:
        return None

    # إنشاء شبكة
    xi = np.linspace(x.min() - 0.1, x.max() + 0.1, 80)
    yi = np.linspace(y.min() - 0.1, y.max() + 0.1, 80)
    xi, yi = np.meshgrid(xi, yi)

    try:
        zi = _interpolate_idw(x, y, z, xi, yi)
    except Exception:
        return None

    fig = go.Figure()

    # Heatmap
    fig.add_trace(go.Contour(
        x=xi[0], y=yi[:, 0], z=zi,
        colorscale=colorscale,
        showscale=False,
        contours=dict(showlines=False),
        hovertemplate=f"<b>{title}</b><br>Lon: %{{x:.3f}}<br>Lat: %{{y:.3f}}<br>Value: %{{z:.1f}} {unit}<extra></extra>"
    ))

    # نقاط المواقع
    fig.add_trace(go.Scatter(
        x=x, y=y, mode='markers',
        marker=dict(size=6, color='black', symbol='circle',
                    line=dict(color='white', width=1)),
        text=df["site"].values if "site" in df.columns else None,
        hovertemplate="<b>%{text}</b><br>Value: %{customdata:.1f}<extra></extra>",
        customdata=z,
        showlegend=False
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=11, color="#5c2c16"),
                   x=0.5, xanchor='center'),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False,
                   scaleanchor="x", scaleratio=1),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=250,
        width=280
    )

    return fig


def generate_auto_maps(df, output_path=None):
    """
    توليد لوحة الخرائط الكاملة (12 خريطة).
    
    Parameters:
    -----------
    df : DataFrame
        يجب أن يحتوي على:
        - lon, lat
        - D_rating, R_rating, A_rating, S_rating, T_rating, I_rating, C_rating
        - CN, Hg
        - DRASTIC, DRASTIC_Tox
    output_path : str, optional
        إذا محدد، يتم حفظ الصورة كـ HTML.
    
    Returns:
    --------
    plotly.graph_objects.Figure
    """
    # التحقق من الأعمدة
    required = ["lon", "lat", "D_rating", "R_rating", "A_rating",
                "S_rating", "T_rating", "I_rating", "C_rating",
                "CN", "Hg", "DRASTIC", "DRASTIC_Tox"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"أعمدة مفقودة: {missing}")

    if len(df) < 3:
        raise ValueError(f"يجب توفير 3 مواقع على الأقل. لديك {len(df)}.")

    # لوحة 3×4
    fig = make_subplots(
        rows=3, cols=4,
        subplot_titles=(
            "D - العمق", "R - التغذية", "A - الخزان", "S - التربة",
            "T - الميل", "I - التهوية", "C - التوصيلية", "CN - سيانيد",
            "Hg - زئبق", "DRASTIC", "DRASTIC-Tox", ""
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.06
    )

    # الخرائط
    maps = [
        ("D_rating", "Greens"),
        ("R_rating", "Blues"),
        ("A_rating", "Purp"),
        ("S_rating", "YlOrBr"),
        ("T_rating", "Reds"),
        ("I_rating", "Teal"),
        ("C_rating", "BuGn"),
        ("CN", "OrRd"),
        ("Hg", "YlOrRd"),
        ("DRASTIC", "Viridis"),
        ("DRASTIC_Tox", "Turbo"),
    ]

    positions = [(1,1), (1,2), (1,3), (1,4),
                 (2,1), (2,2), (2,3), (2,4),
                 (3,1), (3,2), (3,3)]

    x = df["lon"].values
    y = df["lat"].values

    for (col, cmap), (r, c) in zip(maps, positions):
        z = df[col].values

        if col in ("CN", "Hg"):
            # تركيزات الملوثات: نقاط القياس فقط، بلا استيفاء بين المواقع
            fig.add_trace(
                go.Scatter(
                    x=x, y=y, mode='markers',
                    marker=dict(size=9, color=z, colorscale=cmap, showscale=False,
                                line=dict(color='black', width=0.5)),
                    showlegend=False,
                    hovertemplate=f"{col}: %{{marker.color:.4f}} mg/L<extra></extra>"
                ),
                row=r, col=c
            )
            continue

        try:
            xi = np.linspace(x.min() - 0.1, x.max() + 0.1, 60)
            yi = np.linspace(y.min() - 0.1, y.max() + 0.1, 60)
            xi_grid, yi_grid = np.meshgrid(xi, yi)
            zi = _interpolate_idw(x, y, z, xi_grid, yi_grid)
        except Exception:
            continue

        fig.add_trace(
            go.Contour(
                x=xi, y=yi, z=zi,
                colorscale=cmap,
                showscale=False,
                contours=dict(showlines=False),
                hoverinfo='skip'
            ),
            row=r, col=c
        )

        # نقاط المواقع
        fig.add_trace(
            go.Scatter(
                x=x, y=y, mode='markers',
                marker=dict(size=4, color='black'),
                showlegend=False, hoverinfo='skip'
            ),
            row=r, col=c
        )

    fig.update_layout(
        title=dict(
            text="🗺️ الخرائط التلقائية — DRASTIC-Tox",
            font=dict(size=18, color="#5c2c16"),
            x=0.5, xanchor='center'
        ),
        height=900,
        width=1200,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='#faf8f3'
    )

    # إخفاء المحاور
    for i in range(1, 4):
        for j in range(1, 5):
            fig.update_xaxes(showgrid=False, showticklabels=False,
                             zeroline=False, row=i, col=j)
            fig.update_yaxes(showgrid=False, showticklabels=False,
                             zeroline=False, row=i, col=j)

    if output_path:
        fig.write_html(output_path)

    return fig


def prepare_df_for_maps(df, get_rating_funcs):
    """
    تحضير DataFrame من قاعدة البيانات للرسم.
    
    Parameters:
    -----------
    df : DataFrame
        يحتوي على: lat, lon, D, R, A, S, T, I, C, CN, Hg, DRASTIC, DRASTIC_Tox
    get_rating_funcs : tuple
        (get_d_rating, get_r_rating, get_a_rating, get_s_rating,
         get_t_rating, get_i_rating, get_c_rating)
    
    Returns:
    --------
    DataFrame جاهز للرسم
    """
    get_d, get_r, get_a, get_s, get_t, get_i, get_c = get_rating_funcs

    out = df.copy()
    out["D_rating"] = out["depth_m"].apply(get_d)
    out["R_rating"] = out["recharge_mm"].apply(get_r)
    out["A_rating"] = out["aquifer"].apply(get_a)
    out["S_rating"] = out["soil"].apply(get_s)
    out["T_rating"] = out["slope_pct"].apply(get_t)
    out["I_rating"] = out["vadose"].apply(get_i)
    out["C_rating"] = out["conductivity"].apply(get_c)

    if "site" not in out.columns:
        out["site"] = out.get("site_name", out.index.astype(str))

    return out


ONE_MAP_LAYERS = [
    ("DRASTIC", "DRASTIC", "Viridis"),
    ("DRASTIC_Tox", "DRASTIC-Tox", "Turbo"),
    ("CN", "CN (mg/L)", "Reds"),
    ("Hg", "Hg (mg/L)", "Reds"),
    ("D_rating", "D: العمق", "Greens"),
    ("R_rating", "R: التغذية", "Blues"),
    ("A_rating", "A: الخزان", "Purp"),
    ("S_rating", "S: التربة", "YlOrBr"),
    ("T_rating", "T: الميل", "Reds"),
    ("I_rating", "I: غير المشبعة", "Teal"),
    ("C_rating", "C: الناقلية", "BuGn"),
]


def generate_single_map(df):
    """خريطة واحدة لكل المواقع. قائمة منسدلة تختار الطبقة المعروضة، والمرور على أي نقطة يعرض كل القيم."""
    import plotly.graph_objects as go

    required = ["lon", "lat", "site", "DRASTIC", "DRASTIC_Tox", "CN", "Hg",
                "D_rating", "R_rating", "A_rating", "S_rating", "T_rating", "I_rating", "C_rating"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"أعمدة مفقودة: {missing}")

    has_src = "coord_source" in df.columns
    custom = [[str(r.site), round(float(r.DRASTIC), 1), round(float(r.DRASTIC_Tox), 1),
               round(float(r.CN), 4), round(float(r.Hg), 4),
               f"{r.D_rating}/{r.R_rating}/{r.A_rating}/{r.S_rating}/{r.T_rating}/{r.I_rating}/{r.C_rating}",
               str(r.coord_source) if has_src else ""]
              for r in df.itertuples()]
    hover = ("<b>%{customdata[0]}</b><br>DRASTIC: %{customdata[1]}<br>DRASTIC-Tox: %{customdata[2]}"
             "<br>CN: %{customdata[3]} mg/L<br>Hg: %{customdata[4]} mg/L"
             "<br>التقييمات D/R/A/S/T/I/C: %{customdata[5]}<br>الإحداثيات: %{customdata[6]}<extra></extra>")

    # Plotly الحديثة (6+) تستبدل Scattermapbox بـ Scattermap. ندعم الاثنين.
    if hasattr(go, "Scattermap"):
        TraceCls, layout_key = go.Scattermap, "map"
    else:
        TraceCls, layout_key = go.Scattermapbox, "mapbox"

    # مركز ومستوى تكبير يناسبان امتداد النقاط، بدل عرض ثابت يصغّر المواقع
    lat_span = float(df["lat"].max() - df["lat"].min())
    lon_span = float(df["lon"].max() - df["lon"].min())
    span = max(lat_span, lon_span, 0.5)
    zoom = 6.0 if span < 2 else 5.0 if span < 5 else 4.2 if span < 10 else 3.6

    fig = go.Figure()
    for i, (col, label, cmap) in enumerate(ONE_MAP_LAYERS):
        fig.add_trace(TraceCls(
            lat=df["lat"].values, lon=df["lon"].values, mode="markers",
            marker=dict(size=16, color=df[col].values, colorscale=cmap, showscale=True,
                        colorbar=dict(title=dict(text=label), thickness=14, len=0.6, x=1.0)),
            customdata=custom, hovertemplate=hover, visible=(i == 0), name=label))

    buttons = []
    for i, (_, label, _) in enumerate(ONE_MAP_LAYERS):
        buttons.append(dict(label=label, method="update",
                            args=[{"visible": [j == i for j in range(len(ONE_MAP_LAYERS))]},
                                  {"title.text": f"{label} — المواقع المقاسة (إحداثيات تقريبية)"}]))

    fig.update_layout(**{layout_key: dict(style="open-street-map",
                    center=dict(lat=float(df["lat"].mean()), lon=float(df["lon"].mean())), zoom=zoom)},
        title=dict(text=f"{ONE_MAP_LAYERS[0][1]} — المواقع المقاسة", x=0.5, font=dict(size=14)),
        margin=dict(l=0, r=0, t=40, b=0), height=460,
        updatemenus=[dict(buttons=buttons, direction="down", x=0.01, y=0.99, showactive=True,
                          bgcolor="white")],
    )
    return fig
