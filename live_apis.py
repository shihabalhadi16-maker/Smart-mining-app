"""
Live API Integration — DRASTIC-Tox v58.8
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Fetches real-time and historical environmental data:
    - NASA POWER: Climate (rainfall, temp, humidity, wind)
    - Open-Meteo: Historical precipitation
    - Open-Elevation: Terrain elevation
    - SoilGrids (ISRIC): Soil properties

All APIs are free and require NO API keys.
"""
import requests
import numpy as np
from datetime import datetime, timedelta


# ============================================================
# 1. NASA POWER — Climate Data
# ============================================================
def fetch_nasa_power(lat, lon, years=3, parameters=None):
    """
    Fetch climate data from NASA POWER API.

    Parameters
    ----------
    lat, lon : float
    years : int
        Number of past years (default 3)
    parameters : list of str
        Default: ['PRECTOTCORR', 'T2M', 'RH2M', 'WS2M', 'T2M_MAX', 'T2M_MIN']

    Returns
    -------
    dict with keys: rainfall_mm, temperature_c, humidity_pct, wind_ms, ...
    """
    if parameters is None:
        parameters = ['PRECTOTCORR', 'T2M', 'RH2M', 'WS2M', 'T2M_MAX', 'T2M_MIN']

    end_date = datetime.now() - timedelta(days=5)
    start_date = end_date - timedelta(days=365 * years)

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": ",".join(parameters),
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON",
        "header": "true",
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return {"error": f"NASA POWER HTTP {r.status_code}"}

        data = r.json()
        props = data.get("properties", {}).get("parameter", {})

        if not props:
            return {"error": "No data in NASA POWER response"}

        def _mean(key):
            vals = [v for v in props.get(key, {}).values() if isinstance(v, (int, float)) and v > -900]
            return round(float(np.mean(vals)), 2) if vals else None

        def _sum(key):
            vals = [v for v in props.get(key, {}).values() if isinstance(v, (int, float)) and v > -900]
            return round(float(np.sum(vals)), 1) if vals else None

        annual_rain = _sum("PRECTOTCORR") / years if _sum("PRECTOTCORR") else None

        return {
            "rainfall_mm_annual": round(annual_rain, 1) if annual_rain else None,
            "temperature_c": _mean("T2M"),
            "temperature_max_c": _mean("T2M_MAX"),
            "temperature_min_c": _mean("T2M_MIN"),
            "humidity_pct": _mean("RH2M"),
            "wind_speed_ms": _mean("WS2M"),
            "n_years": years,
            "source": "NASA POWER",
            "lat": lat, "lon": lon,
        }
    except requests.exceptions.Timeout:
        return {"error": "NASA POWER timeout (30s)"}
    except Exception as e:
        return {"error": f"NASA POWER: {str(e)[:80]}"}


# ============================================================
# 2. Open-Meteo — Historical Precipitation
# ============================================================
def fetch_open_meteo_precipitation(lat, lon, years=5):
    """
    Fetch historical daily precipitation from Open-Meteo Archive API.

    Returns
    -------
    dict with: annual_rainfall_mm, monthly_avg, dry_season_months, source
    """
    end_date = datetime.now() - timedelta(days=7)
    start_date = end_date - timedelta(days=365 * years)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return {"error": f"Open-Meteo HTTP {r.status_code}"}

        data = r.json()
        daily = data.get("daily", {})
        precip = daily.get("precipitation_sum", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        dates = daily.get("time", [])

        if not precip:
            return {"error": "No precipitation data"}

        precip_clean = [p for p in precip if isinstance(p, (int, float))]
        total = sum(precip_clean)
        annual = total / years if years > 0 else total

        # Monthly aggregation
        monthly = {i: 0 for i in range(1, 13)}
        for date_str, p in zip(dates, precip):
            if not isinstance(p, (int, float)):
                continue
            try:
                month = int(date_str.split("-")[1])
                monthly[month] += p
            except Exception:
                continue

        # Average monthly
        monthly_avg = {m: round(v / years, 1) for m, v in monthly.items()}

        # Dry months (< 20mm)
        dry_months = [m for m, v in monthly_avg.items() if v < 20]

        # Temperature
        tmax_clean = [t for t in tmax if isinstance(t, (int, float))]
        tmin_clean = [t for t in tmin if isinstance(t, (int, float))]
        temp_mean = round((np.mean(tmax_clean) + np.mean(tmin_clean)) / 2, 1) if tmax_clean and tmin_clean else None

        return {
            "annual_rainfall_mm": round(annual, 1),
            "monthly_avg_mm": monthly_avg,
            "dry_season_months": dry_months,
            "n_dry_months": len(dry_months),
            "temperature_mean_c": temp_mean,
            "n_years": years,
            "source": "Open-Meteo Archive",
            "lat": lat, "lon": lon,
        }
    except requests.exceptions.Timeout:
        return {"error": "Open-Meteo timeout (30s)"}
    except Exception as e:
        return {"error": f"Open-Meteo: {str(e)[:80]}"}


# ============================================================
# 3. Open-Elevation — Terrain
# ============================================================
def fetch_elevation(lat, lon):
    """
    Fetch elevation at a point from Open-Elevation API.

    Returns
    -------
    dict with: elevation_m, source
    """
    url = "https://api.open-elevation.com/api/v1/lookup"
    payload = {"locations": [{"latitude": lat, "longitude": lon}]}

    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code != 200:
            return {"error": f"Open-Elevation HTTP {r.status_code}"}

        data = r.json()
        results = data.get("results", [])
        if not results:
            return {"error": "No elevation data"}

        return {
            "elevation_m": round(results[0].get("elevation", 0), 1),
            "source": "Open-Elevation",
        }
    except Exception as e:
        return {"error": f"Open-Elevation: {str(e)[:80]}"}


def fetch_elevation_grid(lat, lon, radius_km=5.0):
    """
    Fetch elevation at 5 points (center + 4 cardinal) to estimate slope.

    Returns
    -------
    dict with: slope_pct, elevation_m, elevation_range_m
    """
    deg_per_km_lat = 1 / 111.0
    deg_per_km_lon = 1 / (111.0 * np.cos(np.radians(lat)))

    dlat = radius_km * deg_per_km_lat
    dlon = radius_km * deg_per_km_lon

    locations = [
        {"latitude": lat, "longitude": lon},          # center
        {"latitude": lat + dlat, "longitude": lon},   # north
        {"latitude": lat - dlat, "longitude": lon},   # south
        {"latitude": lat, "longitude": lon + dlon},   # east
        {"latitude": lat, "longitude": lon - dlon},   # west
    ]

    url = "https://api.open-elevation.com/api/v1/lookup"
    try:
        r = requests.post(url, json={"locations": locations}, timeout=25)
        if r.status_code != 200:
            return {"error": f"Open-Elevation grid HTTP {r.status_code}"}

        data = r.json()
        results = data.get("results", [])
        if len(results) < 5:
            return {"error": f"Only {len(results)} elevation points returned"}

        z_center = results[0].get("elevation", 0)
        z_north = results[1].get("elevation", 0)
        z_south = results[2].get("elevation", 0)
        z_east = results[3].get("elevation", 0)
        z_west = results[4].get("elevation", 0)

        # Calculate slope from N-S and E-W gradients
        dz_ns = abs(z_north - z_south)
        dz_ew = abs(z_east - z_west)
        dist_ns_m = 2 * radius_km * 1000
        dist_ew_m = 2 * radius_km * 1000

        slope_ns = dz_ns / dist_ns_m * 100
        slope_ew = dz_ew / dist_ew_m * 100
        slope_pct = round(np.sqrt(slope_ns ** 2 + slope_ew ** 2), 2)

        elevations = [z_center, z_north, z_south, z_east, z_west]

        return {
            "slope_pct": slope_pct,
            "elevation_m": round(z_center, 1),
            "elevation_range_m": round(max(elevations) - min(elevations), 1),
            "radius_km": radius_km,
            "source": "Open-Elevation (5-point grid)",
        }
    except Exception as e:
        return {"error": f"Open-Elevation grid: {str(e)[:80]}"}


# ============================================================
# 4. SoilGrids (ISRIC) — Soil Properties
# ============================================================
def fetch_soilgrids(lat, lon):
    """
    Fetch soil properties from ISRIC SoilGrids REST API.

    Returns
    -------
    dict with: clay_pct, sand_pct, silt_pct, soc_g_kg, bulk_density
    """
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    properties = ["clay", "sand", "silt", "soc", "bdod"]
    params = {
        "lon": lon,
        "lat": lat,
        "property": properties,
        "depth": "0-5cm",
        "value": "mean",
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return {"error": f"SoilGrids HTTP {r.status_code}"}

        data = r.json()
        layers = data.get("properties", {}).get("layers", [])

        result = {"source": "ISRIC SoilGrids"}
        for layer in layers:
            name = layer.get("name")
            depths = layer.get("depths", [])
            if not depths:
                continue
            val = depths[0].get("values", {}).get("mean")
            if val is None:
                continue

            if name == "clay":
                result["clay_pct"] = round(val / 10, 1)
            elif name == "sand":
                result["sand_pct"] = round(val / 10, 1)
            elif name == "silt":
                result["silt_pct"] = round(val / 10, 1)
            elif name == "soc":
                result["soc_g_kg"] = round(val / 10, 2)
            elif name == "bdod":
                result["bulk_density_kg_m3"] = round(val / 100, 0)

        return result
    except Exception as e:
        return {"error": f"SoilGrids: {str(e)[:80]}"}


# ============================================================
# 5. HELPER — Auto-classification
# ============================================================
def classify_aquifer_from_soil(sand_pct, clay_pct):
    """Rough guess of aquifer type from soil composition."""
    if sand_pct is None:
        return "massive_sandstone"
    if sand_pct > 70:
        return "sand_and_gravel"
    if sand_pct > 40:
        return "massive_sandstone"
    if clay_pct is not None and clay_pct > 40:
        return "massive_shale"
    return "massive_sandstone"


def classify_soil_from_texture(sand_pct, clay_pct, silt_pct):
    """Classify USDA soil texture from percentages."""
    if sand_pct is None:
        return "sandy_loam"
    if sand_pct > 85:
        return "sand"
    if sand_pct > 70:
        return "sandy_loam"
    if clay_pct is not None and clay_pct > 40:
        return "clay_loam"
    if silt_pct is not None and silt_pct > 50:
        return "silty_loam"
    return "loam"


def estimate_recharge_from_rainfall(annual_rainfall_mm, soil_type="sandy_loam", slope_pct=5.0):
    """
    Estimate recharge using simplified FAO method.

    Recharge ≈ Rainfall × (1 - runoff) × infiltration_factor

    Returns recharge in mm/year.
    """
    if annual_rainfall_mm is None:
        return None

    # Infiltration factor by soil type
    infiltration_factors = {
        "sand": 0.25,
        "sandy_loam": 0.15,
        "loam": 0.12,
        "silty_loam": 0.10,
        "clay_loam": 0.08,
        "clay": 0.05,
    }
    inf = infiltration_factors.get(soil_type, 0.12)

    # Runoff factor increases with slope
    runoff_factor = min(0.6, slope_pct / 50.0)

    recharge = annual_rainfall_mm * (1 - runoff_factor) * inf
    return round(max(0, recharge), 1)
