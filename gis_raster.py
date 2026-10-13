"""
gis_raster.py  v61 - drop-in replacement for v58.9.2 (same public function names)

Fixes
  * IDW used Euclidean distance in DEGREES (a degree of longitude is shorter than a degree of
    latitude): now great-circle (haversine) distance in km
  * the double Python loop is replaced by a vectorised computation
  * IDW/kriging returned a value for EVERY cell of the bounding box, however far from any sample:
    cells farther than max_distance_km from the nearest sample are now NaN (no data)
  * export_geotiff wrote the array upside down (row 0 must be the NORTH edge): flipped, float32,
    NaN as nodata
  * statistics / classification / coverage now ignore NaN cells; coverage uses real cell areas
  * kriging variance is returned (uncertainty map), and a warning is given when n is too small
    for a variogram (< 30 points)
  * _validate_points was defined but never used: now used, and its warnings are returned
Interpolating an index computed at a handful of points is a visual aid, NOT a vulnerability map.
"""
import numpy as np

SUDAN_BOUNDS = {"min_lon": 21.8, "max_lon": 38.6, "min_lat": 3.5, "max_lat": 22.2}
SUDAN_ACTUAL_AREA_KM2 = 1_881_000
EARTH_RADIUS_KM = 6371.0
DEFAULT_MAX_DISTANCE_KM = 150.0


# ------------------------------------------------------------------ helpers
def _validate_points(points):
    warnings, valid = [], []
    for p in points:
        if len(p) < 3:
            continue
        try:
            lat, lon, val = float(p[0]), float(p[1]), float(p[2])
        except (TypeError, ValueError):
            continue
        if not np.isfinite([lat, lon, val]).all():
            continue
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            warnings.append(f"Invalid coordinates: ({lat:.3f}, {lon:.3f})")
            continue
        if not (SUDAN_BOUNDS["min_lat"] - 2 <= lat <= SUDAN_BOUNDS["max_lat"] + 2 and
                SUDAN_BOUNDS["min_lon"] - 2 <= lon <= SUDAN_BOUNDS["max_lon"] + 2):
            warnings.append(f"Point outside Sudan bounds: ({lat:.3f}, {lon:.3f})")
        valid.append((lat, lon, val))
    return valid, warnings


def _clip_to_sudan(lon_min, lon_max, lat_min, lat_max, tolerance=2.0):
    """Clips to the Sudan BOUNDING BOX (+tolerance), not to the real border polygon."""
    return (max(lon_min, SUDAN_BOUNDS["min_lon"] - tolerance), min(lon_max, SUDAN_BOUNDS["max_lon"] + tolerance),
            max(lat_min, SUDAN_BOUNDS["min_lat"] - tolerance), min(lat_max, SUDAN_BOUNDS["max_lat"] + tolerance))


def _compute_spherical_area_km2(lon_min, lon_max, lat_min, lat_max):
    dlon = np.radians(lon_max - lon_min)
    return abs(float(EARTH_RADIUS_KM ** 2 * dlon * (np.sin(np.radians(lat_max)) - np.sin(np.radians(lat_min)))))


def _has_pykrige():
    try:
        from pykrige.ok import OrdinaryKriging  # noqa: F401
        return True
    except ImportError:
        return False


def _has_rasterio():
    try:
        import rasterio  # noqa: F401
        return True
    except ImportError:
        return False


def _haversine_km(lat1, lon1, lat2, lon2):
    """Pairwise distances: (N,) x (M,) -> (N, M)."""
    p1, p2 = np.radians(lat1)[:, None], np.radians(lat2)[None, :]
    dphi = p2 - p1
    dlmb = np.radians(lon2)[None, :] - np.radians(lon1)[:, None]
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _grid(lats, lons, resolution, padding):
    lat_min, lat_max, lon_min, lon_max = lats.min(), lats.max(), lons.min(), lons.max()
    lr, lo = max(lat_max - lat_min, 0.1), max(lon_max - lon_min, 0.1)
    lat_min -= lr * padding; lat_max += lr * padding
    lon_min -= lo * padding; lon_max += lo * padding
    lon_min, lon_max, lat_min, lat_max = _clip_to_sudan(lon_min, lon_max, lat_min, lat_max)
    return np.linspace(lon_min, lon_max, resolution), np.linspace(lat_min, lat_max, resolution), \
        (lon_min, lon_max, lat_min, lat_max)


def _result(raster, extent, glons, glats, method, n_pts, warnings, nearest, extra=None):
    out = {"raster": raster, "extent": list(extent), "lons": glons, "lats": glats, "method": method,
           "n_points": n_pts, "warnings": warnings,
           "min_val": float(np.nanmin(raster)) if np.isfinite(raster).any() else None,
           "max_val": float(np.nanmax(raster)) if np.isfinite(raster).any() else None,
           "mean_val": float(np.nanmean(raster)) if np.isfinite(raster).any() else None,
           "std_val": float(np.nanstd(raster)) if np.isfinite(raster).any() else None,
           "valid_cell_fraction": round(float(np.isfinite(raster).mean()), 3),
           "max_distance_km": float(nearest) if nearest is not None else None}
    if extra:
        out.update(extra)
    return out


def _prep(points, resolution, padding):
    valid, warns = _validate_points(points)
    if not valid:
        return None, None, None, None, None, None, None, warns
    pts = np.array(valid, dtype=float)
    lats, lons, vals = pts[:, 0], pts[:, 1], pts[:, 2]
    glons, glats, ext = _grid(lats, lons, resolution, padding)
    GLON, GLAT = np.meshgrid(glons, glats)
    return lats, lons, vals, glons, glats, ext, (GLAT.ravel(), GLON.ravel()), warns


# ------------------------------------------------------------------ interpolation
def idw_interpolation(points, resolution=100, power=2.0, padding=0.05,
                      max_distance_km=DEFAULT_MAX_DISTANCE_KM):
    """IDW with haversine distance. Cells farther than max_distance_km from every sample = NaN."""
    lats, lons, vals, glons, glats, ext, (cl, co), warns = _prep(points, resolution, padding)
    if lats is None:
        return {"error": "No valid points provided"}
    D = _haversine_km(cl, co, lats, lons)                     # (cells, n)
    nearest = D.min(axis=1)
    W = 1.0 / np.maximum(D, 1e-6) ** power
    z = (W * vals[None, :]).sum(axis=1) / W.sum(axis=1)
    z[nearest > max_distance_km] = np.nan
    raster = z.reshape(resolution, resolution)
    if len(vals) < 10:
        warns.append(f"Only {len(vals)} sample points: the surface is a visual aid, not a map.")
    return _result(raster, ext, glons, glats, "IDW", len(vals), warns, max_distance_km, None)


def kriging_interpolation(points, resolution=100, variogram_model="linear", padding=0.05,
                          max_distance_km=DEFAULT_MAX_DISTANCE_KM):
    if not _has_pykrige():
        return {"error": "pykrige not installed — falling back to IDW"}
    from pykrige.ok import OrdinaryKriging
    lats, lons, vals, glons, glats, ext, (cl, co), warns = _prep(points, resolution, padding)
    if lats is None or len(vals) < 4:
        return {"error": "Kriging requires at least 4 points"}
    if len(vals) < 30:
        warns.append(f"Kriging with {len(vals)} points (< 30): the variogram is not reliable.")
    try:
        OK = OrdinaryKriging(lons, lats, vals, variogram_model=variogram_model, verbose=False,
                             enable_plotting=False)
        z, ss = OK.execute("grid", glons, glats)
        raster, var = np.array(z, dtype=float), np.array(ss, dtype=float)
        nearest = _haversine_km(cl, co, lats, lons).min(axis=1).reshape(resolution, resolution)
        raster[nearest > max_distance_km] = np.nan
        var[nearest > max_distance_km] = np.nan
        return _result(raster, ext, glons, glats, f"Kriging ({variogram_model})", len(vals), warns,
                       max_distance_km, {"variance": var})
    except Exception as e:
        return {"error": f"Kriging failed: {str(e)[:100]}"}


# ------------------------------------------------------------------ export / plot
def export_geotiff(raster_result, output_path, crs="EPSG:4326"):
    if not _has_rasterio():
        return {"success": False, "message": "rasterio not installed"}
    import rasterio
    from rasterio.transform import from_bounds
    try:
        arr = np.flipud(np.asarray(raster_result["raster"], dtype="float32"))   # row 0 = north
        lon_min, lon_max, lat_min, lat_max = raster_result["extent"]
        h, w = arr.shape
        with rasterio.open(output_path, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
                           crs=crs, transform=from_bounds(lon_min, lat_min, lon_max, lat_max, w, h),
                           nodata=np.nan) as dst:
            dst.write(arr, 1)
        return {"success": True, "path": output_path, "message": f"GeoTIFF saved ({w}x{h})"}
    except Exception as e:
        return {"success": False, "message": f"Export failed: {str(e)[:100]}"}


def create_raster_plotly(raster_result, title="Raster Surface", colorscale="RdYlGn_r", points=None):
    """points: optional [(lat, lon, value), ...] drawn as markers (shows where data really exists)."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None
    raster = raster_result["raster"]
    lon_min, lon_max, lat_min, lat_max = raster_result["extent"]
    x = np.linspace(lon_min, lon_max, raster.shape[1])
    y = np.linspace(lat_min, lat_max, raster.shape[0])
    fig = go.Figure()
    fig.add_trace(go.Heatmap(z=raster, x=x, y=y, colorscale=colorscale, colorbar=dict(title="Index"),
                             hovertemplate="Lon: %{x:.3f}<br>Lat: %{y:.3f}<br>Value: %{z:.1f}<extra></extra>"))
    fig.add_trace(go.Contour(z=raster, x=x, y=y, contours=dict(showlabels=True, labelfont=dict(size=10, color="white")),
                             line=dict(width=1, color="rgba(255,255,255,0.6)"), showscale=False, hoverinfo="skip"))
    if points:
        fig.add_trace(go.Scatter(x=[p[1] for p in points], y=[p[0] for p in points], mode="markers",
                                 marker=dict(size=9, color="black", symbol="x"), name="Samples",
                                 hovertemplate="Value: %{text}<extra></extra>", text=[f"{p[2]:.1f}" for p in points]))
    fig.update_layout(title=title, xaxis_title="Longitude", yaxis_title="Latitude", height=600,
                      margin=dict(l=40, r=40, t=60, b=40))
    return fig


# ------------------------------------------------------------------ statistics
def _valid_area_km2(raster_result):
    r = raster_result["raster"]
    lon_min, lon_max, lat_min, lat_max = raster_result["extent"]
    h, w = r.shape
    edges = np.radians(np.linspace(lat_min, lat_max, h + 1))
    row_area = EARTH_RADIUS_KM ** 2 * np.radians((lon_max - lon_min) / w) * np.abs(np.sin(edges[1:]) - np.sin(edges[:-1]))
    return float((np.isfinite(r) * row_area[:, None]).sum())


def compute_raster_statistics(raster_result):
    flat = raster_result["raster"].ravel()
    flat = flat[np.isfinite(flat)]
    if flat.size == 0:
        return {"error": "No valid cells (all farther than max_distance_km from any sample)"}
    pct = lambda p: float(np.percentile(flat, p))
    area = _valid_area_km2(raster_result)
    return {"min": float(flat.min()), "max": float(flat.max()), "mean": float(flat.mean()),
            "std": float(flat.std()), "median": float(np.median(flat)),
            "p10": pct(10), "p25": pct(25), "p75": pct(75), "p90": pct(90),
            "n_cells": int(flat.size), "valid_cell_fraction": raster_result.get("valid_cell_fraction"),
            "coverage_km2": round(area, 2),
            "percent_of_sudan": round(area / SUDAN_ACTUAL_AREA_KM2 * 100, 2)}


def classify_raster(raster_result, thresholds=None):
    if thresholds is None:
        thresholds = [100, 140, 180]
    flat = raster_result["raster"].ravel()
    flat = flat[np.isfinite(flat)]
    total = flat.size
    if total == 0:
        return {"error": "No valid cells"}
    parts = {"low": int((flat < thresholds[0]).sum()),
             "medium": int(((flat >= thresholds[0]) & (flat < thresholds[1])).sum()),
             "high": int(((flat >= thresholds[1]) & (flat < thresholds[2])).sum()),
             "very_high": int((flat >= thresholds[2]).sum())}
    out = {k: {"count": v, "percent": round(v / total * 100, 1)} for k, v in parts.items()}
    out["total"] = total
    return out
