"""Build processed datasets from raw inputs.

Outputs (data/processed):
  gdw_barriers_global.csv   slim copy of GDW v1.0 barriers (all countries)
  iran_dams_gdw.csv         GDW barriers inside Iran
  iran_bases.csv            Alma (2026) launch bases with decimal coordinates
  iran_grid.csv             10-arcmin cells inside Iran with covariates
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
import netCDF4 as nc
from shapely.geometry import Point
from shapely import contains_xy
from scipy.ndimage import maximum_filter, minimum_filter

from common import RAW, EXT, PROC, balltree, nn_km, densify_lines_to_points, iran_polygon, load_bases

KEEP = ["GDW_ID", "DAM_NAME", "DAM_TYPE", "COUNTRY", "ADMIN_UNIT", "RIVER", "YEAR_DAM", "DAM_HGT_M",
        "CAP_MCM", "AREA_SKM", "POWER_MW", "MAIN_USE", "USE_IRRI", "USE_ELEC", "USE_SUPP", "USE_FCON",
        "ORIG_SRC", "GRAND_ID", "LONG_DAM", "LAT_DAM"]


def gdw():
    g = gpd.read_file(EXT / "GDW_v1_0_shp" / "GDW_barriers_v1_0.shp")
    df = g[KEEP].copy()
    df["lon"], df["lat"] = g.geometry.x.values, g.geometry.y.values
    df.to_csv(PROC / "gdw_barriers_global.csv", index=False)
    poly = iran_polygon()
    inside = contains_xy(poly.buffer(0.02), df.lon.values, df.lat.values)
    ir = df[(df.COUNTRY == "Iran") | inside].drop_duplicates("GDW_ID")
    ir.to_csv(PROC / "iran_dams_gdw.csv", index=False)
    print(f"GDW global {len(df)}, Iran {len(ir)} (country field {int((df.COUNTRY=='Iran').sum())})")
    return ir


def bases():
    b = load_bases()
    b.to_csv(PROC / "iran_bases.csv", index=False)
    return b


def grid():
    d = nc.Dataset(RAW / "earth-topography-10arcmin.nc")
    lon = d["longitude"][:].data
    lat = d["latitude"][:].data
    z = d["topography"][:].data.astype(float)
    relief = maximum_filter(z, size=3) - minimum_filter(z, size=3)  # ~55 km window
    sel_lon = (lon > 43) & (lon < 64)
    sel_lat = (lat > 24) & (lat < 40.5)
    LON, LAT = np.meshgrid(lon[sel_lon], lat[sel_lat])
    Z = z[np.ix_(sel_lat, sel_lon)]
    RL = relief[np.ix_(sel_lat, sel_lon)]
    poly = iran_polygon()
    m = contains_xy(poly, LON.ravel(), LAT.ravel())
    cells = pd.DataFrame({"lon": LON.ravel()[m], "lat": LAT.ravel()[m],
                          "elev": Z.ravel()[m], "relief": RL.ravel()[m]})
    # covariates: distance to settlement, river, coast
    pp = gpd.read_file(RAW / "ne_10m_populated_places_simple.geojson")
    pp = pp[(pp.adm0_a3 == "IRN") & (pp.pop_max >= 50000)]
    t = balltree(pp.geometry.x.values, pp.geometry.y.values)
    cells["d_city"] = nn_km(t, cells.lon.values, cells.lat.values)
    riv = gpd.read_file(RAW / "globalmap_iran" / "riverl_irn.shp").to_crs(4326)
    rp = densify_lines_to_points(riv)
    tr = balltree(rp[:, 0], rp[:, 1])
    cells["d_river"] = nn_km(tr, cells.lon.values, cells.lat.values)
    coast = coast_points()
    tc = balltree(coast[:, 0], coast[:, 1])
    cells["d_coast"] = nn_km(tc, cells.lon.values, cells.lat.values)
    cells.to_csv(PROC / "iran_grid.csv", index=False)
    print(f"grid cells in Iran: {len(cells)}; Natural Earth places >=50k: {len(pp)}; river pts {len(rp)}")
    return cells


def coast_points():
    """Sea coast incl. Caspian (Natural Earth 10m coastline treats the Caspian as sea)."""
    c = gpd.read_file(RAW / "ne_10m_coastline.geojson")
    c = c.cx[40:66, 22:43]
    return densify_lines_to_points(c)


def add_point_covariates(df: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    """Attach covariates to arbitrary points: terrain from the nearest grid cell, distances computed directly."""
    tg = balltree(cells.lon.values, cells.lat.values)
    _, idx = tg.query(np.radians(np.c_[df.lat.values, df.lon.values]), k=1)
    out = df.copy()
    for k in ("elev", "relief"):
        out[k] = cells[k].values[idx[:, 0]]
    pp = gpd.read_file(RAW / "ne_10m_populated_places_simple.geojson")
    pp = pp[(pp.adm0_a3 == "IRN") & (pp.pop_max >= 50000)]
    out["d_city"] = nn_km(balltree(pp.geometry.x.values, pp.geometry.y.values), out.lon.values, out.lat.values)
    riv = gpd.read_file(RAW / "globalmap_iran" / "riverl_irn.shp").to_crs(4326)
    rp = densify_lines_to_points(riv)
    out["d_river"] = nn_km(balltree(rp[:, 0], rp[:, 1]), out.lon.values, out.lat.values)
    cp = coast_points()
    out["d_coast"] = nn_km(balltree(cp[:, 0], cp[:, 1]), out.lon.values, out.lat.values)
    return out


if __name__ == "__main__":
    if (EXT / "GDW_v1_0_shp" / "GDW_barriers_v1_0.shp").exists():
        gdw()
    else:
        print("GDW shapefile not found in data/external; using committed data/processed/gdw_barriers_global.csv")
    b = bases()
    cells = grid()
    add_point_covariates(b, cells).to_csv(PROC / "iran_bases.csv", index=False)
