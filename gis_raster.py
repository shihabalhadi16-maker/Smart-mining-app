"""
GIS Raster Support — DRASTIC-Tox v58.9.2
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Converts point-based risk data into continuous raster surfaces via:
    - IDW (Inverse Distance Weighting) — always available
    - Kriging — requires pykrige (optional)
    - GeoTIFF export — requires rasterio (optional)

Changelog:
    v58.9.2 (2025-10) — Fix Coverage calculation (spherical formula),
                        add Sudan bounds clipping, add outlier detection
    v58.9.1 (2025-10) — Fix per-row mining_type handling
    v58.7   (2025-09) — Initial release with IDW + Kriging + GeoTIFF

Provides:
    - idw_interpolation(points, resolution, power)
    - kriging_interpolation(points, resolution)
    - export_geotiff(raster, bounds, path)
    - create_raster_plotly(raster, bounds, title)
    - compute_raster_statistics(raster)
    - classify_raster(raster, thresholds)
"""
import numpy as np


# ============================================================
# CONSTANTS — Sudan geographic bounds
# ============================================================
SUDAN_BOUNDS = {
    "min_lon": 21.8,
    "max_lon": 38.6,
    "min_lat": 3.5,
    "max_lat": 22.2,
}

# Sudan's actual surface area (km²) — for coverage comparison
SUDAN_ACTUAL_AREA_KM2 = 1_881_000

# Earth's mean radius (km)
EARTH_RADIUS_KM = 6371.0


# ============================================================
# OPTIONAL DEPENDENCIES
# ============================================================
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


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def _validate_points(points):
    """
    Validate points, detect outliers.

    Returns
    -------
    (valid_points, warnings) : (list, list of str)
    """
    warnings = []
    valid = []

    for p in points:
        if len(p) < 3:
            continue
        lat, lon, val = float(p[0]), float(p[1]), float(p[2])

        # Skip invalid coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            warnings.append(f"Invalid coordinates: ({lat:.3f}, {lon:.3f})")
            continue

        # Warn if outside Sudan region (with 5° tolerance)
        if not (SUDAN_BOUNDS["min_lat"] - 5 <= lat <= SUDAN_BOUNDS["max_lat"] + 5):
            warnings.append(
                f"Latitude outlier: {lat:.3f} (outside Sudan ± 5°)"
            )
        if not (SUDAN_BOUNDS["min_lon"] - 5 <= lon <= SUDAN_BOUNDS["max_lon"] + 5):
            warnings.append(
                f"Longitude outlier: {lon:.3f} (outside Sudan ± 5°)"
            )

        valid.append((lat, lon, val))

    return valid, warnings


def _clip_to_sudan(lon_min, lon_max, lat_min, lat_max, tolerance=2.0):
    """
    Clip raster extent to Sudan borders.

    Parameters
    ----------
    tolerance : float
        Degrees of tolerance around Sudan (default 2°)

    Returns
    -------
    (lon_min, lon_max, lat_min, lat_max) : tuple
    """
    return (
        max(lon_min, SUDAN_BOUNDS["min_lon"] - tolerance),
        min(lon_max, SUDAN_BOUNDS["max_lon"] + tolerance),
        max(lat_min, SUDAN_BOUNDS["min_lat"] - tolerance),
        min(lat_max, SUDAN_BOUNDS["max_lat"] + tolerance),
    )


def _compute_spherical_area_km2(lon_min, lon_max, lat_min, lat_max):
    """
    Compute exact geographic area on a sphere (km²).

    Formula:
        A = R² × ΔLon(rad) × (sin(lat_max) - sin(lat_min))

    Parameters
    ----------
    lon_min, lon_max, lat_min, lat_max : float
        Degrees

    Returns
    -------
    area_km2 : float
    """
    dlon_rad = np.radians(lon_max - lon_min)
    lat_min_rad = np.radians(lat_min)
    lat_max_rad = np.radians(lat_max)

    area_km2 = (
        EARTH_RADIUS_KM ** 2
        * dlon_rad
        * (np.sin(lat_max_rad) - np.sin(lat_min_rad))
    )
    return abs(float(area_km2))


def _prepare_grid_bounds(lats, lons, padding):
    """
    Compute raster extent with padding, then clip to Sudan.

    Returns
    -------
    (lon_min, lon_max, lat_min, lat_max) : tuple
    """
    lat_min, lat_max = float(lats.min()), float(lats.max())
    lon_min, lon_max = float(lons.min()), float(lons.max())

    lat_range = max(lat_max - lat_min, 0.1)
    lon_range = max(lon_max - lon_min, 0.1)

    lat_min -= lat_range * padding
    lat_max += lat_range * padding
    lon_min -= lon_range * padding
    lon_max += lon_range * padding

    # Clip to Sudan
    lon_min, lon_max, lat_min, lat_max = _clip_to_sudan(
        lon_min, lon_max, lat_min, lat_max
    )

    return lon_min, lon_max, lat_min, lat_max


# ============================================================
# IDW INTERPOLATION
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
        - raster: 2D numpy array (resolution × resolution)
        - extent: [lon_min, lon_max, lat_min, lat_max]
        - lons: 1D array of longitudes
        - lats: 1D array of latitudes
        - method: "IDW"
        - n_points: number of input points
        - warnings: list of warnings (if any)
    """
    valid, warnings = _validate_points(points)
    if len(valid) == 0:
        return {"error": "No valid points provided"}

    pts = np.array(valid, dtype=float)
    lats, lons, vals = pts[:, 0], pts[:, 1], pts[:, 2]

    # Compute bounds with padding + Sudan clip
    lon_min, lon_max, lat_min, lat_max = _prepare_grid_bounds(
        lats, lons, padding
    )

    # Create grid
    grid_lons = np.linspace(lon_min, lon_max, resolution)
    grid_lats = np.linspace(lat_min, lat_max, resolution)
    glon, glat = np.meshgrid(grid_lons, grid_lats)

    # IDW calculation (vectorized for speed)
    raster = np.zeros((resolution, resolution), dtype=float)

    for i in range(resolution):
        for j in range(resolution):
            d = np.sqrt(
                (glat[i, j] - lats) ** 2 + (glon[i, j] - lons) ** 2
            )
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
        "warnings": warnings,
    }


# ============================================================
# KRIGING INTERPOLATION
# ============================================================
def kriging_interpolation(points, resolution=100, variogram_model="linear", padding=0.05):
    """
    Kriging interpolation. Requires pykrige.

    Returns same structure as idw_interpolation, or {"error": ...}.
    """
    if not _has_pykrige():
        return {"error": "pykrige not installed — falling back to IDW"}

    from pykrige.ok import OrdinaryKriging

    valid, warnings = _validate_points(points)
    if len(valid) < 4:
        return {"error": "Kriging requires at least 4 points"}

    pts = np.array(valid, dtype=float)
    lats, lons, vals = pts[:, 0], pts[:, 1], pts[:, 2]

    # Compute bounds with padding + Sudan clip
    lon_min, lon_max, lat_min, lat_max = _prepare_grid_bounds(
        lats, lons, padding
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
            "warnings": warnings,
        }
    except Exception as e:
        return {"error": f"Kriging failed: {str(e)[:100]}"}


# ============================================================
# GEOTIFF EXPORT
# ============================================================
def export_geotiff(raster_result, output_path, crs="EPSG:4326"):
    """
    Export raster to GeoTIFF. Requires rasterio.
    """
    if not _has_rasterio():
        return {"success": False, "message": "rasterio not installed"}

    import rasterio
    from rasterio.transform import from_bounds

    try:
        raster = raster_result["raster"]
        lon_min, lon_max, lat_min, lat_max = raster_result["extent"]
        height, width = raster.shape

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
            dst.write(raster, 1)

        return {
            "success": True,
            "path": output_path,
            "message": f"GeoTIFF saved ({width}×{height})",
        }
    except Exception as e:
        return {"success": False, "message": f"Export failed: {str(e)[:100]}"}


# ============================================================
# PLOTLY VISUALIZATION
# ============================================================
def create_raster_plotly(raster_result, title="Raster Surface", colorscale="RdYlGn_r"):
    """
    Create Plotly heatmap + contour overlay for the raster.

    Returns a plotly Figure object.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    raster = raster_result["raster"]
    lon_min, lon_max, lat_min, lat_max = raster_result["extent"]

    fig = go.Figure()

    # Heatmap
    fig.add_trace(go.Heatmap(
        z=raster,
        x=np.linspace(lon_min, lon_max, raster.shape[1]),
        y=np.linspace(lat_min, lat_max, raster.shape[0]),
        colorscale=colorscale,
        colorbar=dict(title="Index"),
        hovertemplate=(
            "Lon: %{x:.3f}<br>"
            "Lat: %{y:.3f}<br>"
            "Value: %{z:.1f}<extra></extra>"
        ),
    ))

    # Contour lines
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
# STATISTICS — ⭐ FIXED IN v58.9.2
# ============================================================
def compute_raster_statistics(raster_result):
    """
    Compute extended statistics for raster.

    v58.9.2 — Fixed coverage calculation:
        - Uses exact spherical formula (not flat rectangle)
        - Clips to Sudan bounds
        - Reports % of Sudan's actual area
        - Distinguishes bounding-box area from actual region
    """
    raster = raster_result["raster"]
    flat = raster.flatten()
    lon_min, lon_max, lat_min, lat_max = raster_result["extent"]

    def pct(p):
        return float(np.percentile(flat, p))

    # ============ CORRECT GEOGRAPHIC AREA ============
    # Exact spherical formula
    extent_area_km2 = _compute_spherical_area_km2(
        lon_min, lon_max, lat_min, lat_max
    )

    # Equivalent area using cos(mean_lat) — for reference
    mean_lat = (lat_min + lat_max) / 2.0
    cos_lat = np.cos(np.radians(mean_lat))
    equivalent_area_km2 = (
        (lon_max - lon_min) * 111.0 * cos_lat
        * (lat_max - lat_min) * 111.0
    )

    # Compare with Sudan
    percent_of_sudan = (extent_area_km2 / SUDAN_ACTUAL_AREA_KM2) * 100

    # Determine note
    if extent_area_km2 > SUDAN_ACTUAL_AREA_KM2:
        note = "⚠️ Extent larger than Sudan — check input coordinates"
    elif percent_of_sudan < 5:
        note = "Small localized study area"
    elif percent_of_sudan < 30:
        note = "Regional study area"
    else:
        note = "Large-scale study area"

    return {
        # Raster value statistics
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

        # ✅ FIXED coverage metrics
        "coverage_km2": round(extent_area_km2, 2),
        "equivalent_area_km2": round(equivalent_area_km2, 2),
        "percent_of_sudan": round(percent_of_sudan, 2),
        "coverage_note": note,

        # Extent info
        "extent_lon_range": round(lon_max - lon_min, 3),
        "extent_lat_range": round(lat_max - lat_min, 3),
        "extent_center_lat": round(mean_lat, 3),
    }


# ============================================================
# CLASSIFICATION
# ============================================================
def classify_raster(raster_result, thresholds=None):
    """
    Classify raster cells into risk levels.

    Default thresholds: [100, 140, 180] (Medium/High/Very High).
    Returns dict with counts and percentages.
    """
    if thresholds is None:
        thresholds = [100, 140, 180]

    raster = raster_result["raster"]
    flat = raster.flatten()
    total = flat.size

    low = int((flat < thresholds[0]).sum())
    medium = int(((flat >= thresholds[0]) & (flat < thresholds[1])).sum())
    high = int(((flat >= thresholds[1]) & (flat < thresholds[2])).sum())
    very_high = int((flat >= thresholds[2]).sum())

    return {
        "low": {"count": low, "percent": round(low / total * 100, 1)},
        "medium": {"count": medium, "percent": round(medium / total * 100, 1)},
        "high": {"count": high, "percent": round(high / total * 100, 1)},
        "very_high": {"count": very_high, "percent": round(very_high / total * 100, 1)},
        "total": total,
        "thresholds": thresholds,
    }


# ============================================================
# SELF-TEST (run: python gis_raster.py)
# ============================================================
if __name__ == "__main__":
    # Test with 5 sample points in Sudan
    test_points = [
        (13.5, 33.6, 155.0),   # Sennar — contaminated
        (15.3, 36.4, 88.0),    # Kassala — clean
        (17.9, 34.0, 96.0),    # Berber — clean
        (19.6, 33.3, 98.0),    # Abu Hamad — clean
        (15.6, 32.5, 100.0),   # North Khartoum — contaminated
    ]

    print("=" * 60)
    print("GIS Raster — Self Test (v58.9.2)")
    print("=" * 60)

    result = idw_interpolation(test_points, resolution=50)
    stats = compute_raster_statistics(result)

    print(f"\nMethod: {result['method']}")
    print(f"Points: {result['n_points']}")
    print(f"Warnings: {result.get('warnings', [])}")
    print(f"\n--- Raster Statistics ---")
    print(f"Min:      {stats['min']:.2f}")
    print(f"Max:      {stats['max']:.2f}")
    print(f"Mean:     {stats['mean']:.2f}")
    print(f"Median:   {stats['median']:.2f}")
    print(f"Std:      {stats['std']:.2f}")
    print(f"\n--- Coverage (FIXED) ---")
    print(f"Coverage (km²):    {stats['coverage_km2']:,.2f}")
    print(f"Percent of Sudan:  {stats['percent_of_sudan']:.2f}%")
    print(f"Note:              {stats['coverage_note']}")
    print(f"\n--- Extent ---")
    print(f"Extent: {result['extent']}")
    print(f"Lon range: {stats['extent_lon_range']}°")
    print(f"Lat range: {stats['extent_lat_range']}°")

    print("\n--- Classification ---")
    cls = classify_raster(result)
    for level in ["low", "medium", "high", "very_high"]:
        print(f"{level:10s}: {cls[level]['count']:5d} cells ({cls[level]['percent']}%)")

    print("\n" + "=" * 60)
    print("✅ Self-test completed successfully")
    print("=" * 60)
