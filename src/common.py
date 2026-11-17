"""Shared paths, loaders and geodesic helpers."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
EXT = ROOT / "data" / "external"
PROC = ROOT / "data" / "processed"
RES = ROOT / "results"
TAB = RES / "tables"
FIG = ROOT / "report" / "figures"
for p in (PROC, TAB, FIG):
    p.mkdir(parents=True, exist_ok=True)

R_EARTH_KM = 6371.0088
SEED = 20261116


def dms_to_dd(s: str) -> float:
    """Convert strings like 32°27'23"N to decimal degrees."""
    m = re.match(r"\s*(\d+)°(\d+)'([\d.]+)\"?([NSEW])", s)
    if not m:
        raise ValueError(s)
    d, mi, se, h = m.groups()
    v = float(d) + float(mi) / 60 + float(se) / 3600
    return -v if h in "SW" else v


def balltree(lon: np.ndarray, lat: np.ndarray) -> BallTree:
    return BallTree(np.radians(np.c_[lat, lon]), metric="haversine")


def nn_km(tree: BallTree, lon: np.ndarray, lat: np.ndarray, k: int = 1) -> np.ndarray:
    d, _ = tree.query(np.radians(np.c_[lat, lon]), k=k)
    return d[:, 0] * R_EARTH_KM if k == 1 else d * R_EARTH_KM


def densify_lines_to_points(gdf: gpd.GeoDataFrame, step_deg: float = 0.02) -> np.ndarray:
    """Return (lon, lat) vertices of line geometries densified at ~step_deg (~2 km)."""
    pts = []
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            continue
        parts = getattr(geom, "geoms", [geom])
        for g in parts:
            if g.geom_type == "Polygon":
                g = g.exterior
            L = g.length
            n = max(int(L / step_deg), 1)
            for t in np.linspace(0, L, n + 1):
                p = g.interpolate(t)
                pts.append((p.x, p.y))
    return np.array(pts)


def iran_polygon():
    c = gpd.read_file(RAW / "ne_10m_admin_0_countries.geojson")
    return c.loc[c.ADM0_A3 == "IRN"].geometry.union_all()


def load_bases() -> pd.DataFrame:
    b = pd.read_csv(RAW / "iran_missile_bases_alma_2026.csv")
    b["lat"] = b.lat_dms.map(dms_to_dd)
    b["lon"] = b.lon_dms.map(dms_to_dd)
    return b


def load_iran_dams() -> pd.DataFrame:
    return pd.read_csv(PROC / "iran_dams_gdw.csv")
