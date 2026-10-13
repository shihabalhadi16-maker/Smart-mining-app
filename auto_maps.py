"""
auto_maps.py v61 - 12-panel overview maps (D, R, A, S, T, I, C, CN, Hg, DRASTIC, DRASTIC-Tox, class)

Fixes vs v56:
  * generate_auto_maps accepts show_sudan (app.py passes it; the old signature raised TypeError)
  * no more 'nearest-value' fill over the whole bounding box: cells farther than max_distance_km
    from any sample are left EMPTY (the old maps painted regions with no data)
  * distances in km (degrees distort with latitude); duplicate locations (dry/wet) are averaged
  * last panel is a real 4-class map, not a copy of DRASTIC-Tox
  * ratings are ordinal classes: they are shown as interpolated surfaces for orientation only
"""
import numpy as np
import pandas as pd

R_EARTH = 6371.0088


def _xy_km(lon, lat, lat0):
    return (np.radians(np.asarray(lon, float)) * R_EARTH * np.cos(np.radians(lat0)),
            np.radians(np.asarray(lat, float)) * R_EARTH)


def _dedupe(x, y, z, decimals=2):
    d = pd.DataFrame({"x": np.round(x, decimals), "y": np.round(y, decimals), "z": z})
    g = d.groupby(["x", "y"], as_index=False)["z"].mean()
    return g["x"].values, g["y"].values, g["z"].values


def _interpolate_idw(x, y, z, xi, yi, power=2.0, max_km=150.0):
    """IDW in km; NaN where the nearest sample is farther than max_km (None = no mask)."""
    x, y, z = _dedupe(np.asarray(x, float), np.asarray(y, float), np.asarray(z, float))
    lat0 = float(np.mean(y))
    px, py = _xy_km(x, y, lat0)
    gx, gy = _xy_km(xi.ravel(), yi.ravel(), lat0)
    dist = np.sqrt((gx[:, None] - px[None, :]) ** 2 + (gy[:, None] - py[None, :]) ** 2)
    nearest = dist.min(axis=1)
    w = 1.0 / np.maximum(dist, 1e-6) ** power
    zi = (w * z[None, :]).sum(axis=1) / w.sum(axis=1)
    if max_km is not None:
        zi = np.where(nearest <= max_km, zi, np.nan)
    return zi.reshape(xi.shape)


def _class_from_tox(v, th=(100.0, 140.0, 180.0)):
    return np.where(np.isnan(v), np.nan, np.digitize(v, th).astype(float))


def generate_auto_maps(df, output_path=None, show_sudan=True, max_distance_km=150.0):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    required = ["lon", "lat", "D_rating", "R_rating", "A_rating", "S_rating", "T_rating", "I_rating",
                "C_rating", "CN", "Hg", "DRASTIC", "DRASTIC_Tox"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"أعمدة مفقودة: {missing}")
    df = df.dropna(subset=required)
    if len(df.drop_duplicates(["lon", "lat"])) < 3:
        raise ValueError("يجب توفير 3 مواقع مستقلة (إحداثيات مختلفة) على الأقل.")
    titles = ("D - العمق", "R - التغذية", "A - الخزان", "S - التربة", "T - الميل", "I - التهوية",
              "C - التوصيلية", "CN - سيانيد", "Hg - زئبق", "DRASTIC", "DRASTIC-Tox (تجريبي)", "فئة DRASTIC-Tox")
    maps = [("D_rating", "Greens"), ("R_rating", "Blues"), ("A_rating", "Purp"), ("S_rating", "YlOrBr"),
            ("T_rating", "Reds"), ("I_rating", "Teal"), ("C_rating", "BuGn"), ("CN", "OrRd"), ("Hg", "YlOrRd"),
            ("DRASTIC", "Viridis"), ("DRASTIC_Tox", "Turbo"), ("CLASS", [[0, "#388e3c"], [.33, "#fbc02d"], [.66, "#f57c00"], [1, "#d32f2f"]])]
    fig = make_subplots(rows=3, cols=4, subplot_titles=titles, vertical_spacing=0.12, horizontal_spacing=0.06)
    x, y = df["lon"].values, df["lat"].values
    xi = np.linspace(x.min() - 0.3, x.max() + 0.3, 60)
    yi = np.linspace(y.min() - 0.3, y.max() + 0.3, 60)
    xg, yg = np.meshgrid(xi, yi)
    for i, (col, cmap) in enumerate(maps):
        r, c = i // 4 + 1, i % 4 + 1
        src = "DRASTIC_Tox" if col == "CLASS" else col
        zi = _interpolate_idw(x, y, df[src].values.astype(float), xg, yg, max_km=max_distance_km)
        kw = {}
        if col == "CLASS":
            zi = _class_from_tox(zi); kw = dict(zmin=0, zmax=3)
        fig.add_trace(go.Heatmap(x=xi, y=yi, z=zi, colorscale=cmap, showscale=False, hoverinfo="skip", **kw), row=r, col=c)
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=4, color="black"), showlegend=False, hoverinfo="skip"), row=r, col=c)
        fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=False, row=r, col=c)
        fig.update_yaxes(showgrid=False, showticklabels=False, zeroline=False, row=r, col=c)
    fig.update_layout(title=dict(text=f"🗺️ الخرائط التلقائية — الخلايا الأبعد من {int(max_distance_km)} كم عن أقرب عيّنة مُخفاة",
                                 font=dict(size=16, color="#5c2c16"), x=0.5, xanchor="center"),
                      height=900, width=1200, showlegend=False, plot_bgcolor="white", paper_bgcolor="#faf8f3")
    if output_path:
        fig.write_html(output_path)
    return fig


def prepare_df_for_maps(df, get_rating_funcs):
    get_d, get_r, get_a, get_s, get_t, get_i, get_c = get_rating_funcs
    out = df.copy()
    out["D_rating"] = out["depth_m"].astype(float).apply(get_d)
    out["R_rating"] = out["recharge_mm"].astype(float).apply(get_r)
    out["A_rating"] = out["aquifer"].astype(str).apply(get_a)
    out["S_rating"] = out["soil"].astype(str).apply(get_s)
    out["T_rating"] = out["slope_pct"].astype(float).apply(get_t)
    out["I_rating"] = out["vadose"].astype(str).apply(get_i)
    out["C_rating"] = out["conductivity"].astype(float).apply(get_c)
    if "site" not in out.columns:
        out["site"] = out["site_name"] if "site_name" in out.columns else out.index.astype(str)
    return out
