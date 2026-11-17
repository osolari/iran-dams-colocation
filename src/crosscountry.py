"""Dam building under water scarcity: Iran in comparative perspective.

1. Dam density (dams per 10,000 km2) from national/official counts.
2. Construction timelines from GDW v1.0 (dams with a recorded completion year).
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from common import RAW, PROC, TAB, FIG
import style

style.apply()


def areas() -> pd.Series:
    c = gpd.read_file(RAW / "ne_10m_admin_0_countries.geojson")
    c = c.to_crs("+proj=cea +lon_0=0 +lat_ts=30 +datum=WGS84 +units=m")  # equal area
    return pd.Series(c.geometry.area.values / 1e6, index=c.ADM0_A3.values)


def density_table():
    o = pd.read_csv(RAW / "official_dam_counts.csv")
    a = areas()
    o["area_km2"] = o.adm0_a3.map(a)
    o["dams_per_10k_km2"] = o.dams / o.area_km2 * 1e4
    o = o.sort_values("dams_per_10k_km2", ascending=False)
    o.to_csv(TAB / "dam_density_official.csv", index=False)
    return o


def timelines():
    g = pd.read_csv(PROC / "gdw_barriers_global.csv", low_memory=False)
    g = g[g.YEAR_DAM.between(1900, 2025)]
    countries = ["Iran", "Turkey", "Spain", "Morocco", "Algeria", "United States"]
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.8), sharex=True)
    out = {}
    for ax, c in zip(axes.ravel(), countries):
        s = g[g.COUNTRY == c].YEAR_DAM
        dec = (s // 5 * 5).value_counts().sort_index()
        ax.bar(dec.index + 2.5, dec.values, width=4.2, color=style.CRIMSON if c == "Iran" else style.STEEL)
        peak = int(dec.idxmax())
        ax.set_title(f"{c}\nn = {len(s)}, peak {peak}–{peak+4}", fontsize=8.5)
        ax.set_xlim(1900, 2026)
        out[c] = {"n_with_year": int(len(s)), "peak_5yr": peak, "median_year": float(s.median()),
                  "share_after_1990": float((s >= 1990).mean())}
    for ax in axes[-1]:
        ax.set_xlabel("Completion year (5-yr bins)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Dams completed")
    fig.suptitle("Dam completions per five-year period (GDW v1.0)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig5_timelines.pdf"); plt.close(fig)
    json.dump(out, open(TAB / "dam_timelines_gdw.json", "w"), indent=1)
    return out


def density_fig(o):
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    o = o.sort_values("dams_per_10k_km2")
    cols = [style.CRIMSON if c == "Iran" else style.STEEL for c in o.country]
    ax.barh(o.country, o.dams_per_10k_km2, color=cols, height=0.6)
    for y, (v, n) in enumerate(zip(o.dams_per_10k_km2, o.dams)):
        ax.text(v + 0.4, y, f"{v:.1f} ({n:,} dams)", va="center", fontsize=8, color=style.INK)
    ax.set_xlabel("Dams per 10,000 km²")
    ax.set_xlim(0, o.dams_per_10k_km2.max() * 1.35); ax.grid(axis="y", visible=False)
    ax.set_title("Dam density from national counts")
    fig.savefig(FIG / "fig6_density.pdf"); plt.close(fig)


if __name__ == "__main__":
    o = density_table(); print(o[["country", "dams", "area_km2", "dams_per_10k_km2"]])
    density_fig(o)
    print(json.dumps(timelines(), indent=1))
