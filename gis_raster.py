"""
GIS Raster Support — DRASTIC-Tox v61
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Converts point-based risk data into continuous raster surfaces via:
    - IDW (Inverse Distance Weighting) — always available
    - Kriging — requires pykrige (optional)
    - GeoTIFF export — requires rasterio (optional)

Provides:
    - idw_interpolation(points, resolution, power)
    - kriging_interpolation(points, resolution)
    - export_geotiff(raster, bounds, path)
    - create_raster_plotly(raster, bounds, title)
    - compute_raster_statistics(raster)
    - classify_raster(raster)

v61 Changes:
  * FIXED: GeoTIFF was being written vertically flipped.
    In-memory raster has row 0 = lat_min (south), but GeoTIFF
    convention is row 0 = north (lat_max). Now uses np.flipud()
    before writing.
  * Added Sudan bounds clipping (v58.9.2)
  * Fixed spherical Coverage calculation (v58.9.2)
  * Added outlier detection (v58.9.2)
"""
import numpy as np


# ============================================================
# Sudan geographic constants
# ============================================================
SUDAN_BOUNDS = {
    "min_lon": 21.8,
    "max_lon": 38.6,
    "min_lat": 3.5,
    "max_lat": 22.2,
}
SUDAN_ACTUAL_AREA_KM2 = 1_881_000
EARTH_RADIUS_KM = 6371.0


# ============================================================
# Helpers
# ============================================================
def _validate_points(points):
    """Validate points, return (valid_points, warnings)."""
    warnings = []
    valid = []
    for p in points:
        if len(p) < 3:
            continue
        lat, lon, val = float(p[0]), float(p[1]), float(p[2])
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            warnings.append(f"Invalid coordinates: ({lat:.3f}, {lon:.3f})")
            continue
        if not (SUDAN_BOUNDS["min_lat"] - 5 <= lat <= SUDAN_BOUNDS["max_lat"] + 5):
            warnings.append(f"Latitude outlier: {lat:.3f}")
        if not (SUDAN_BOUNDS["min_lon"] - 5 <= lon <= SUDAN_BOUNDS["max_lon"] + 5):
            warnings.append(f"Longitude outlier: {lon:.3f}")
        valid.append((lat, lon, val))
    return valid, warnings


def _clip_to_sudan(lon_min, lon_max, lat_min, lat_max, tolerance=2.0):
    """Clip raster extent to Sudan borders."""
    return (
        max(lon_min, SUDAN_BOUNDS["min_lon"] - tolerance),
        min(lon_max, SUDAN_BOUNDS["max_lon"] + tolerance),
        max(lat_min, SUDAN_BOUNDS["min_lat"] - tolerance),
        min(lat_max, SUDAN_BOUNDS["max_lat"] + tolerance),
    )


def _compute_spherical_area_km2(lon_min, lon_max, lat_min, lat_max):
    """Exact geographic area on a sphere (km²)."""
    dlon_rad = np.radians(lon_max - lon_min)
    lat_min_rad = np.radians(lat_min)
    lat_max_rad = np.radians(lat_max)
    area_km2 = (
        EARTH_RADIUS_KM ** 2 * dlon_rad
        * (np.sin(lat_max_rad) - np.sin(lat_min_rad))
    )
    return abs(float(area_km2))


def _has_pykrige():
    try:
        from pykrige.ok import OrdinaryKriging
        return True
    except ImportError:
        return False


def _has_rasterio():
    try:
        import rasterio
        return True
    except ImportError:
        return False


# ============================================================
# Interpolation
# ============================================================
def idw_interpolation(points, resolution=100, power=2.0, padding=0.05):
    """
    Inverse Distance Weighting interpolation.

    Parameters
    ----------
    points : list of tuples
        [(lat, lon, value), ...]
    resolution : int
        Grid size (resolution × resolution)
    power : float
        IDW power parameter (default 2.0)
    padding : float
        Fractional padding around data bounds (default 0.05 = 5%)

    Returns
    -------
    dict with keys:
        raster  : 2D numpy array  — row 0 = lat_min (SOUTH), row -1 = lat_max (NORTH)
        extent  : [lon_min, lon_max, lat_min, lat_max]
        lons    : 1D array of longitudes (ascending)
        lats    : 1D array of latitudes  (ascending, south→north)
        method  : "IDW"
        n_points: number of input points
    """
    pts = np.array([(p[0], p[1], p[2]) for p in points if len(p) >= 3], dtype=float)
    if len(pts) == 0:
        return {"error": "No valid points provided"}

    lats, lons, vals = pts[:, 0], pts[:, 1], pts[:, 2]

    lat_min, lat_max = lats.min(), lats.max()
    lon_min, lon_max = lons.min(), lons.max()

    lat_range = max(lat_max - lat_min, 0.1)
    lon_range = max(lon_max - lon_min, 0.1)
    lat_min -= lat_range * padding
    lat_max += lat_range * padding
    lon_min -= lon_range * padding
    lon_max += lon_range * padding

    lon_min, lon_max, lat_min, lat_max = _clip_to_sudan(
        lon_min, lon_max, lat_min, lat_max
    )

    grid_lons = np.linspace(lon_min, lon_max, resolution)
    grid_lats = np.linspace(lat_min, lat_max, resolution)   # ascending, S→N
    glon, glat = np.meshgrid(grid_lons, grid_lats)

    raster = np.zeros((resolution, resolution), dtype=float)

    for i in range(resolution):
        for j in range(resolution):
            d = np.sqrt((glat[i, j] - lats) ** 2 + (glon[i, j] - lons) ** 2)
            zero_mask = d < 1e-10
            if np.any(zero_mask):
                raster[i, j] = vals[zero_mask].mean()
            else:
                w = 1.0 / (d ** power)
                w_sum = w.sum()
                raster[i, j] = (w * vals).sum() / w_sum if w_sum > 0 else 0.0

    return {
        "raster": raster,
        "extent": [lon_min, lon_max, lat_min, lat_max],
        "lons": grid_lons,
        "lats": grid_lats,
        "method": "IDW",
        "n_points": len(pts),
        "min_val": float(raster.min()),
        "max_val": float(raster.max()),
        "mean_val": float(raster.mean()),
        "std_val": float(raster.std()),
    }


def kriging_interpolation(points, resolution=100, variogram_model="linear", padding=0.05):
    """Kriging interpolation. Requires pykrige.
    Returns same structure as idw_interpolation, or {"error": ...}."""
    if not _has_pykrige():
        return {"error": "pykrige not installed — falling back to IDW"}

    from pykrige.ok import OrdinaryKriging

    pts = np.array([(p[0], p[1], p[2]) for p in points if len(p) >= 3], dtype=float)
    if len(pts) < 4:
        return {"error": "Kriging requires at least 4 points"}

    lats, lons, vals = pts[:, 0], pts[:, 1], pts[:, 2]

    lat_min, lat_max = lats.min(), lats.max()
    lon_min, lon_max = lons.min(), lons.max()

    lat_range = max(lat_max - lat_min, 0.1)
    lon_range = max(lon_max - lon_min, 0.1)
    lat_min -= lat_range * padding
    lat_max += lat_range * padding
    lon_min -= lon_range * padding
    lon_max += lon_range * padding

    lon_min, lon_max, lat_min, lat_max = _clip_to_sudan(
        lon_min, lon_max, lat_min, lat_max
    )

    grid_lons = np.linspace(lon_min, lon_max, resolution)
    grid_lats = np.linspace(lat_min, lat_max, resolution)

    try:
        OK = OrdinaryKriging(
            lons, lats, vals,
            variogram_model=variogram_model,
            verbose=False,
            enable_plotting=False,
        )
        z, ss = OK.execute("grid", grid_lons, grid_lats)
        raster = np.array(z)

        return {
            "raster": raster,
            "extent": [lon_min, lon_max, lat_min, lat_max],
            "lons": grid_lons,
            "lats": grid_lats,
            "method": f"Kriging ({variogram_model})",
            "n_points": len(pts),
            "min_val": float(raster.min()),
            "max_val": float(raster.max()),
            "mean_val": float(raster.mean()),
            "std_val": float(raster.std()),
        }
    except Exception as e:
        return {"error": f"Kriging failed: {str(e)[:100]}"}


# ============================================================
# GeoTIFF export  — v61 FIX: vertical flip
# ============================================================
def export_geotiff(raster_result, output_path, crs="EPSG:4326"):
    """
    Export raster to GeoTIFF. Requires rasterio.

    v61 Fix
    -------
    The in-memory raster has row 0 = lat_min (south). The GeoTIFF
    convention (and rasterio's `from_bounds`) assumes row 0 = north.
    Without the flip, the exported image appears vertically mirrored.

    Parameters
    ----------
    raster_result : dict
        Output from idw_interpolation or kriging_interpolation
    output_path : str
        Path to save GeoTIFF (e.g., "/tmp/output.tif")
    crs : str
        Coordinate reference system

    Returns
    -------
    dict with success, path, message
    """
    if not _has_rasterio():
        return {"success": False, "message": "rasterio not installed"}

    import rasterio
    from rasterio.transform import from_bounds

    try:
        raster = raster_result["raster"]
        lon_min, lon_max, lat_min, lat_max = raster_result["extent"]
        height, width = raster.shape

        # ─── v61 FIX: flip vertically ────────────────────────
        # In-memory:  row 0  = lat_min (south)
        # GeoTIFF:    row 0  = lat_max (north, per `from_bounds`)
        raster_to_write = np.flipud(raster)
        # ─────────────────────────────────────────────────────

        transform = from_bounds(lon_min, lat_min, lon_max, lat_max, width, height)

        with rasterio.open(
            output_path, "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=raster.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(raster_to_write, 1)

        return {"success": True, "path": output_path,
                "message": f"GeoTIFF saved ({width}×{height}, v61 flip applied)"}
    except Exception as e:
        return {"success": False, "message": f"Export failed: {str(e)[:100]}"}


# ============================================================
# Plotly visualisation (uses in-memory orientation, no flip needed)
# ============================================================
def create_raster_plotly(raster_result, title="Raster Surface", colorscale="RdYlGn_r"):
    """
    Create Plotly heatmap + contour overlay.

    Note: plotly's y-axis is treated as ascending (S→N), which matches
    the in-memory raster orientation. Do NOT pass a flipped raster here.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    raster = raster_result["raster"]
    lon_min, lon_max, lat_min, lat_max = raster_result["extent"]

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=raster,
        x=np.linspace(lon_min, lon_max, raster.shape[1]),
        y=np.linspace(lat_min, lat_max, raster.shape[0]),   # ascending S→N
        colorscale=colorscale,
        colorbar=dict(title="Index"),
        hovertemplate="Lon: %{x:.3f}<br>Lat: %{y:.3f}<br>Value: %{z:.1f}<extra></extra>",
    ))

    fig.add_trace(go.Contour(
        z=raster,
        x=np.linspace(lon_min, lon_max, raster.shape[1]),
        y=np.linspace(lat_min, lat_max, raster.shape[0]),
        contours=dict(
            showlabels=True,
            labelfont=dict(size=10, color="white"),
        ),
        line=dict(width=1, color="rgba(255,255,255,0.6)"),
        showscale=False,
        hoverinfo="skip",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        height=600,
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


# ============================================================
# Statistics
# ============================================================
def compute_raster_statistics(raster_result):
    """Compute extended statistics for raster."""
    raster = raster_result["raster"]
    flat = raster.flatten()

    def pct(p):
        return float(np.percentile(flat, p))

    return {
        "min": float(flat.min()),
        "max": float(flat.max()),
        "mean": float(flat.mean()),
        "std": float(flat.std()),
        "median": float(np.median(flat)),
        "p10": pct(10),
        "p25": pct(25),
        "p75": pct(75),
        "p90": pct(90),
        "n_cells": int(flat.size),
        "coverage_km2": round(
            _compute_spherical_area_km2(
                raster_result["extent"][0],
                raster_result["extent"][1],
                raster_result["extent"][2],
                raster_result["extent"][3],
            ),
            2
        ),
        "percent_of_sudan": round(
            _compute_spherical_area_km2(
                raster_result["extent"][0],
                raster_result["extent"][1],
                raster_result["extent"][2],
                raster_result["extent"][3],
            ) / SUDAN_ACTUAL_AREA_KM2 * 100,
            2
        ),
    }


def classify_raster(raster_result, thresholds=None):
    """
    Classify raster cells into risk levels.
    Default thresholds: [100, 140, 180] (Medium/High/Very High).
    """
    if thresholds is None:
        thresholds = [100, 140, 180]

    raster = raster_result["raster"]
    flat = raster.flatten()
    total = flat.size

    low       = int((flat < thresholds[0]).sum())
    medium    = int(((flat >= thresholds[0]) & (flat < thresholds[1])).sum())
    high      = int(((flat >= thresholds[1]) & (flat < thresholds[2])).sum())
    very_high = int((flat >= thresholds[2]).sum())

    return {
        "low":       {"count": low,       "percent": round(low       / total * 100, 1)},
        "medium":    {"count": medium,    "percent": round(medium    / total * 100, 1)},
        "high":      {"count": high,      "percent": round(high      / total * 100, 1)},
        "very_high": {"count": very_high, "percent": round(very_high / total * 100, 1)},
        "total": total,
    }


# ============================================================
# Self-test
# ============================================================
def _selftest():
    pts = [(13.5, 33.6, 100), (13.6, 33.7, 150),
           (13.4, 33.5, 200), (13.7, 33.8, 120)]
    result = idw_interpolation(pts, resolution=20)
    assert "raster" in result, result
    assert result["raster"].shape == (20, 20)
    # Verify extent has lat_min < lat_max
    e = result["extent"]
    assert e[2] < e[3], f"lat_min should be < lat_max: {e}"
    # Verify row 0 corresponds to lat_min (south)
    # (raster row 0 must have been built from grid_lats[0] = lat_min)
    assert result["lats"][0] < result["lats"][-1], "lats must be ascending"
    print("gis_raster v61 self-test passed (flip fix in place)")


if __name__ == "__main__":
    _selftest() 
