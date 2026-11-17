"""Rank countries by how close their military bases sit to water (nearest dam or sea coast).

Bases:  Wikidata items that are instances of military base (Q245016) or any subclass, with coordinates
        (police-type barracks and farms excluded; dissolved sites excluded in the primary analysis).
        Country assigned by point-in-polygon against Natural Earth admin-0.
Water:  dams = Global Dam Watch v1.0 barriers; coast = Natural Earth 10m coastline (densified ~5 km).
Benchmark: for each country, the same distances for uniform random points inside the country, so the
        ranking can also be read relative to each country's own geography (ratio < 1 = bases closer
        to water than the country's land in general).
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely import contains_xy

from common import RAW, PROC, TAB, FIG, SEED, balltree, nn_km, densify_lines_to_points
import style

style.apply()
rng = np.random.default_rng(SEED)
MIN_N = 15
N_RAND = 2000
N_BOOT = 2000

EXCLUDE_CLASSES = {"Q83554028", "Q5645932", "Q134318865", "Q142174816", "Q142175685", "Q116257904"}


def load_bases(include_dissolved=False) -> pd.DataFrame:
    w = pd.read_csv(RAW / "wikidata" / "wikidata_military_bases_raw.csv")
    w["qid"] = w["item"].str.rsplit("/", n=1).str[-1]
    w["cls_qid"] = w["cls"].str.rsplit("/", n=1).str[-1]
    xy = w["coord"].str.split(" ", expand=True).astype(float)
    w["lon"], w["lat"] = xy[0], xy[1]
    w = w[~w.cls_qid.isin(EXCLUDE_CLASSES)]
    if not include_dissolved:
        w = w[w.dissolved.isna()]
    w = w.drop_duplicates("qid")
    return w[["qid", "itemLabel", "cls_qid", "lon", "lat"]].reset_index(drop=True)


def assign_country(df, countries):
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326)
    j = gpd.sjoin(pts, countries[["ADM0_A3", "ADMIN", "geometry"]], how="left", predicate="within")
    return pd.DataFrame(j.drop(columns=["geometry", "index_right"]))


def water_trees():
    g = pd.read_csv(PROC / "gdw_barriers_global.csv", usecols=["lon", "lat"])
    dam_t = balltree(g.lon.values, g.lat.values)
    coast = gpd.read_file(RAW / "ne_10m_coastline.geojson")
    cp = densify_lines_to_points(coast, step_deg=0.05)
    coast_t = balltree(cp[:, 0], cp[:, 1])
    return dam_t, coast_t


def distances(df, dam_t, coast_t):
    out = df.copy()
    out["d_dam"] = nn_km(dam_t, out.lon.values, out.lat.values)
    out["d_coast"] = nn_km(coast_t, out.lon.values, out.lat.values)
    out["d_water"] = np.minimum(out.d_dam, out.d_coast)
    return out


def random_points(poly, n):
    minx, miny, maxx, maxy = poly.bounds
    pts = []
    while sum(len(p) for p in pts) < n:
        # sample uniformly on the sphere within the bounding box
        u = rng.uniform(np.sin(np.radians(miny)), np.sin(np.radians(maxy)), 4 * n)
        la = np.degrees(np.arcsin(u)); lo = rng.uniform(minx, maxx, 4 * n)
        keep = contains_xy(poly, lo, la)
        pts.append(np.c_[lo[keep], la[keep]])
    a = np.vstack(pts)[:n]
    return pd.DataFrame({"lon": a[:, 0], "lat": a[:, 1]})


def boot_ci(x, f=np.median):
    b = f(rng.choice(x, (N_BOOT, len(x)), replace=True), axis=1)
    return float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))


def summarise(d, countries, dam_t, coast_t, label):
    rows = []
    for a3, g in d.groupby("ADM0_A3"):
        if len(g) < MIN_N:
            continue
        poly = countries.loc[countries.ADM0_A3 == a3].geometry.union_all()
        rnd = distances(random_points(poly, N_RAND), dam_t, coast_t)
        r = {"ADM0_A3": a3, "country": g.ADMIN.iloc[0], "n_bases": len(g)}
        for k in ("d_water", "d_dam", "d_coast"):
            x = g[k].values
            r[f"{k}_mean"], r[f"{k}_median"] = float(x.mean()), float(np.median(x))
            r[f"{k}_median_lo"], r[f"{k}_median_hi"] = boot_ci(x)
            r[f"{k}_rand_median"] = float(np.median(rnd[k]))
            r[f"{k}_ratio"] = r[f"{k}_median"] / r[f"{k}_rand_median"] if r[f"{k}_rand_median"] > 0 else np.nan
        rows.append(r)
    t = pd.DataFrame(rows)
    t["rank_median_water"] = t.d_water_median.rank(method="min").astype(int)
    t["rank_mean_water"] = t.d_water_mean.rank(method="min").astype(int)
    t["rank_median_dam"] = t.d_dam_median.rank(method="min").astype(int)
    t["rank_ratio_water"] = t.d_water_ratio.rank(method="min").astype(int)
    t = t.sort_values("d_water_median")
    t.to_csv(TAB / f"country_ranking_{label}.csv", index=False)
    return t


def iran_alma(countries, dam_t, coast_t):
    b = pd.read_csv(PROC / "iran_bases.csv")[["name", "lon", "lat"]]
    b = distances(b, dam_t, coast_t)
    poly = countries.loc[countries.ADM0_A3 == "IRN"].geometry.union_all()
    rnd = distances(random_points(poly, N_RAND), dam_t, coast_t)
    r = {"country": "Iran (25 launch bases, Alma 2026)", "n_bases": len(b)}
    for k in ("d_water", "d_dam", "d_coast"):
        x = b[k].values
        r[f"{k}_mean"], r[f"{k}_median"] = float(x.mean()), float(np.median(x))
        r[f"{k}_median_lo"], r[f"{k}_median_hi"] = boot_ci(x)
        r[f"{k}_rand_median"] = float(np.median(rnd[k]))
        r[f"{k}_ratio"] = r[f"{k}_median"] / r[f"{k}_rand_median"]
    return r


def fig_rank(t, alma, key, fname, title, xlabel):
    t = t.copy()
    t = pd.concat([t, pd.DataFrame([alma])], ignore_index=True)
    t = t.sort_values(f"{key}_median").reset_index(drop=True)
    h = max(4, 0.16 * len(t) + 1)
    fig, ax = plt.subplots(figsize=(6.6, h))
    y = np.arange(len(t))
    is_ir = t.country.str.startswith("Iran")
    lo, hi, md, mn = t[f"{key}_median_lo"], t[f"{key}_median_hi"], t[f"{key}_median"], t[f"{key}_mean"]
    ax.hlines(y, lo, hi, color=style.GRID, lw=3)
    ax.scatter(mn, y, s=14, marker="|", color=style.INK2, label="Mean", zorder=3)
    ax.scatter(md[~is_ir], y[~is_ir], s=16, color=style.BLUE, label="Median (95% bootstrap CI)", zorder=4)
    ax.scatter(md[is_ir], y[is_ir], s=30, color=style.ORANGE, zorder=5, label="Iran")
    ax.set_yticks(y, [f"{c}  (n={n})" for c, n in zip(t.country, t.n_bases)], fontsize=6.5)
    ax.invert_yaxis(); ax.set_xscale("log"); ax.set_xlim(1, 600); ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False); ax.legend(loc="upper right", fontsize=7)
    ax.set_title(title)
    fig.savefig(FIG / fname); plt.close(fig)


def run():
    countries = gpd.read_file(RAW / "ne_10m_admin_0_countries.geojson")
    dam_t, coast_t = water_trees()
    out = {}
    for label, incl in (("current", False), ("incl_dissolved", True)):
        b = assign_country(load_bases(incl), countries)
        b = b.dropna(subset=["ADM0_A3"])
        b = distances(b, dam_t, coast_t)
        b.to_csv(PROC / f"wikidata_bases_{label}.csv", index=False)
        t = summarise(b, countries, dam_t, coast_t, label)
        out[label] = {"n_bases": int(len(b)), "n_countries_ranked": int(len(t)),
                      "iran_wikidata_n": int((b.ADM0_A3 == "IRN").sum())}
        if label == "current":
            alma = iran_alma(countries, dam_t, coast_t)
            out["iran_alma"] = alma
            fig_rank(t, alma, "d_water", "fig7_rank_water.pdf",
                     "Distance from military bases to the nearest dam or coast",
                     "km to nearest dam or sea coast (log scale)")
            fig_rank(t, alma, "d_dam", "fig8_rank_dam.pdf",
                     "Distance from military bases to the nearest dam",
                     "km to nearest dam (log scale)")
            # where would Iran's launch bases rank?
            for key in ("d_water", "d_dam"):
                v = t[f"{key}_median"].values
                out[f"iran_alma_{key}_rank_among"] = {"rank": int((v < alma[f"{key}_median"]).sum() + 1),
                                                      "of": int(len(v) + 1),
                                                      "share_of_countries_closer": float((v < alma[f"{key}_median"]).mean())}
                vr = t[f"{key}_ratio"].values
                out[f"iran_alma_{key}_ratio_rank"] = {"rank": int((vr < alma[f"{key}_ratio"]).sum() + 1), "of": int(len(vr) + 1)}
    json.dump(out, open(TAB / "global_ranking_summary.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    run()
