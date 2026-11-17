"""Is the proximity of Iranian missile bases to dams unusual?

Tests the observed base-to-nearest-dam distances against a hierarchy of null models:
  CSR          uniform random sites inside Iran (what an eyeball map comparison implicitly assumes)
  M1           sites matched on terrain (elevation, relief)
  M2           M1 + distance to nearest city >= 50k
  M3           M2 + distance to nearest mapped river
  RIV          dams re-placed at random along the river network (bases fixed)
Placebo sets (cities, airports) are run through the same CSR test.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from scipy import stats

from common import RAW, PROC, TAB, FIG, SEED, balltree, nn_km, densify_lines_to_points, iran_polygon
from prepare import add_point_covariates
import style

style.apply()
rng = np.random.default_rng(SEED)
NSIM = 10000
K_MATCH = 40
CELL = 1 / 6  # 10 arc-minutes

cells = pd.read_csv(PROC / "iran_grid.csv")
bases = pd.read_csv(PROC / "iran_bases.csv")
dams = pd.read_csv(PROC / "iran_dams_gdw.csv")
dam_tree = balltree(dams.lon.values, dams.lat.values)
large = dams[dams.ORIG_SRC.eq("GRanD") | dams.GRAND_ID.gt(0)]
large_tree = balltree(large.lon.values, large.lat.values)

COVS = {"M1": ["elev", "relief"], "M2": ["elev", "relief", "d_city"],
        "M3": ["elev", "relief", "d_city", "d_river"]}


def stat_block(d: np.ndarray) -> dict:
    return {"median": float(np.median(d)), "mean": float(np.mean(d)),
            "share_le10": float(np.mean(d <= 10)), "share_le20": float(np.mean(d <= 20))}


def jitter(lon, lat):
    return (lon + rng.uniform(-CELL / 2, CELL / 2, lon.shape), lat + rng.uniform(-CELL / 2, CELL / 2, lat.shape))


def sim_csr(n: int, tree, nsim=NSIM) -> np.ndarray:
    """Median NN distance for n uniform points in Iran (cells weighted by area)."""
    w = np.cos(np.radians(cells.lat.values)); w /= w.sum()
    out = np.empty(nsim)
    curves = []
    for s in range(nsim):
        i = rng.choice(len(cells), n, p=w)
        lo, la = jitter(cells.lon.values[i], cells.lat.values[i])
        d = nn_km(tree, lo, la)
        out[s] = np.median(d)
        if s < 2000:
            curves.append(np.sort(d))
    return out, np.array(curves)


def matched_pools(pts: pd.DataFrame, covs: list[str], k=K_MATCH) -> np.ndarray:
    X = cells[covs].values.astype(float)
    mu, sd = X.mean(0), X.std(0)
    Z = (X - mu) / sd
    P = (pts[covs].values - mu) / sd
    d = ((P[:, None, :] - Z[None, :, :]) ** 2).sum(-1)
    return np.argsort(d, axis=1)[:, :k]


def sim_matched(pts, covs, tree, nsim=NSIM):
    pools = matched_pools(pts, covs)
    n = len(pts)
    out = np.empty(nsim); curves = []
    for s in range(nsim):
        j = pools[np.arange(n), rng.integers(0, pools.shape[1], n)]
        lo, la = jitter(cells.lon.values[j], cells.lat.values[j])
        d = nn_km(tree, lo, la)
        out[s] = np.median(d)
        if s < 2000:
            curves.append(np.sort(d))
    # covariate balance: pooled matched cells vs bases
    bal = {c: {"bases_mean": float(pts[c].mean()), "matched_mean": float(cells[c].values[pools.ravel()].mean()),
               "iran_mean": float(cells[c].mean())} for c in COVS["M3"]}
    return out, np.array(curves), bal


def sim_river_dams(pts, nsim=NSIM):
    riv = gpd.read_file(RAW / "globalmap_iran" / "riverl_irn.shp").to_crs(4326)
    rp = densify_lines_to_points(riv)
    out = np.empty(nsim)
    for s in range(nsim):
        k = rp[rng.choice(len(rp), len(dams), replace=False)]
        t = balltree(k[:, 0], k[:, 1])
        out[s] = np.median(nn_km(t, pts.lon.values, pts.lat.values))
    return out


def pval(obs, null):  # one-sided: is observed closer than null?
    return float((1 + np.sum(null <= obs)) / (1 + len(null)))


def run():
    res = {"n_bases": int(len(bases)), "n_dams": int(len(dams)), "n_large_dams": int(len(large)), "nsim": NSIM}
    bases["d_dam"] = nn_km(dam_tree, bases.lon.values, bases.lat.values)
    d_idx = dam_tree.query(np.radians(np.c_[bases.lat, bases.lon]), k=1)[1][:, 0]
    bases["nearest_dam"] = dams.DAM_NAME.fillna("(unnamed)").values[d_idx]
    bases["nearest_dam_year"] = dams.YEAR_DAM.values[d_idx]
    bases["d_large_dam"] = nn_km(large_tree, bases.lon.values, bases.lat.values)
    obs = np.median(bases.d_dam)
    res["observed"] = stat_block(bases.d_dam.values)
    res["observed_large"] = stat_block(bases.d_large_dam.values)

    nulls, curves = {}, {}
    nulls["CSR"], curves["CSR"] = sim_csr(len(bases), dam_tree)
    balance = {}
    for m, cv in COVS.items():
        nulls[m], curves[m], balance[m] = sim_matched(bases, cv, dam_tree)
    nulls["RIV"] = sim_river_dams(bases)
    res["tests"] = {m: {"null_median_of_medians": float(np.median(v)), "null_q025": float(np.quantile(v, .025)),
                        "null_q975": float(np.quantile(v, .975)), "ratio_obs_to_null": float(obs / np.median(v)),
                        "p_one_sided": pval(obs, v)} for m, v in nulls.items()}
    res["balance"] = balance

    # large-dam version (GRanD subset) under CSR and M3
    nl_csr, _ = sim_csr(len(bases), large_tree, nsim=4000)
    nl_m3, _, _ = sim_matched(bases, COVS["M3"], large_tree, nsim=4000)
    obs_l = np.median(bases.d_large_dam)
    res["tests_large"] = {"CSR": {"null_median": float(np.median(nl_csr)), "p": pval(obs_l, nl_csr)},
                          "M3": {"null_median": float(np.median(nl_m3)), "p": pval(obs_l, nl_m3)}}

    # struck vs not struck
    s = bases[bases.struck_june2025 == 1].d_dam; ns = bases[bases.struck_june2025 == 0].d_dam
    u = stats.mannwhitneyu(s, ns, alternative="two-sided")
    res["struck_vs_not"] = {"median_struck": float(s.median()), "median_not": float(ns.median()),
                            "n_struck": int(len(s)), "n_not": int(len(ns)), "mannwhitney_p": float(u.pvalue)}

    # placebo point sets under CSR
    pp = gpd.read_file(RAW / "ne_10m_populated_places_simple.geojson")
    pp = pp[(pp.adm0_a3 == "IRN") & (pp.pop_max >= 50000)]
    air = gpd.read_file(RAW / "globalmap_iran" / "airp_irn.shp") if (RAW / "globalmap_iran" / "airp_irn.shp").exists() else None
    placebo = {"Cities >= 50k (Natural Earth)": pd.DataFrame({"lon": pp.geometry.x, "lat": pp.geometry.y})}
    if air is not None:
        air = air.to_crs(4326)
        placebo["Airports (Global Map Iran)"] = pd.DataFrame({"lon": air.geometry.x, "lat": air.geometry.y})
    res["placebo"] = {}
    for name, df in placebo.items():
        dd = nn_km(dam_tree, df.lon.values, df.lat.values)
        nul, _ = sim_csr(len(df), dam_tree, nsim=4000)
        dfc = add_point_covariates(df, cells)
        nm3, _, _ = sim_matched(dfc, COVS["M3"], dam_tree, nsim=4000)
        res["placebo"][name] = {"n": int(len(df)), "observed_median": float(np.median(dd)),
                                "csr_null_median": float(np.median(nul)), "p_csr": pval(np.median(dd), nul),
                                "m3_null_median": float(np.median(nm3)), "p_m3": pval(np.median(dd), nm3)}

    # attributes of dams near bases vs elsewhere
    dams["d_base"] = nn_km(balltree(bases.lon.values, bases.lat.values), dams.lon.values, dams.lat.values)
    near = dams[dams.d_base <= 25]; far = dams[dams.d_base > 25]
    yr_n, yr_f = near.YEAR_DAM[near.YEAR_DAM > 0], far.YEAR_DAM[far.YEAR_DAM > 0]
    def share(df, col): return float((df[col].fillna("").astype(str).str.len() > 0).mean())
    res["dams_near_vs_far"] = {
        "n_near": int(len(near)), "n_far": int(len(far)),
        "median_year_near": float(yr_n.median()), "median_year_far": float(yr_f.median()),
        "year_mw_p": float(stats.mannwhitneyu(yr_n, yr_f).pvalue),
        "median_cap_near": float(near.CAP_MCM.median()), "median_cap_far": float(far.CAP_MCM.median()),
        "main_use_near": near.MAIN_USE.fillna("Not recorded").value_counts().to_dict(),
        "main_use_far": far.MAIN_USE.fillna("Not recorded").value_counts().to_dict(),
    }

    res["sensitivity"] = sensitivity(bases)

    bases.to_csv(TAB / "iran_bases_nearest_dam.csv", index=False)
    pd.DataFrame(nulls).to_csv(TAB / "iran_null_distributions.csv", index=False)
    with open(TAB / "iran_results.json", "w") as f:
        json.dump(res, f, indent=2, default=str)
    figures(bases, nulls, curves, res)
    print(json.dumps({k: res[k] for k in ("observed", "tests", "tests_large", "struck_vs_not", "placebo")}, indent=1))
    return res


def _draws(pts, covs, k, nsim, tree):
    """Return nsim x n matrix of NN distances for matched (covs) or CSR (covs=None) draws."""
    n = len(pts)
    D = np.empty((nsim, n))
    if covs is None:
        w = np.cos(np.radians(cells.lat.values)); w /= w.sum()
        for s in range(nsim):
            i = rng.choice(len(cells), n, p=w)
            D[s] = nn_km(tree, *jitter(cells.lon.values[i], cells.lat.values[i]))
    else:
        pools = matched_pools(pts, covs, k)
        for s in range(nsim):
            j = pools[np.arange(n), rng.integers(0, k, n)]
            D[s] = nn_km(tree, *jitter(cells.lon.values[j], cells.lat.values[j]))
    return D


def sensitivity(pts, nsim=3000):
    statf = {"median": lambda D: np.median(D, axis=-1), "mean": lambda D: np.mean(D, axis=-1),
             "share_within_20km": lambda D: -np.mean(D <= 20, axis=-1)}  # negated so 'smaller = closer'
    obs = pts.d_dam.values
    rows = []
    for null, covs, ks in (("CSR", None, [None]), ("M1", COVS["M1"], [20, 40, 80]),
                           ("M3", COVS["M3"], [20, 40, 80])):
        for k in ks:
            D = _draws(pts, covs, k, nsim, dam_tree)
            for sname, f in statf.items():
                o, v = f(obs[None, :])[0], f(D)
                rows.append({"null": null, "k": k, "statistic": sname, "p_one_sided": pval(o, v)})
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "iran_sensitivity.csv", index=False)
    return df.to_dict("records")


def figures(bases, nulls, curves, res):
    poly = iran_polygon()
    gx, gy = poly.exterior.xy if poly.geom_type == "Polygon" else max(poly.geoms, key=lambda g: g.area).exterior.xy

    # Fig 1: map
    fig, ax = plt.subplots(figsize=(7, 5.6))
    piv = cells.pivot_table(index="lat", columns="lon", values="elev")
    sc = ax.pcolormesh(piv.columns.values, piv.index.values, np.ma.masked_invalid(piv.values),
                       cmap="Greys", vmin=-500, vmax=3500, shading="nearest", edgecolors="none",
                       antialiased=False, rasterized=True)
    ax.plot(gx, gy, color=style.INK2, lw=0.8)
    ax.scatter(dams.lon, dams.lat, s=14, color=style.STEEL, edgecolor="white", lw=0.5, label=f"Dams, GDW v1.0 (n = {len(dams)})", zorder=3)
    st = bases.struck_june2025 == 1
    ax.scatter(bases.lon[st], bases.lat[st], s=50, marker="^", color=style.CRIMSON, edgecolor="white", lw=0.8,
               label=f"Launch bases struck in June 2025 (n = {st.sum()})", zorder=4)
    ax.scatter(bases.lon[~st], bases.lat[~st], s=50, marker="^", facecolor="white", edgecolor=style.CRIMSON, lw=1.4,
               label=f"Launch bases not struck (n = {(~st).sum()})", zorder=4)
    cb = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.02); cb.set_label("Elevation (m), ETOPO1 at 10 arc-min")
    ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)"); ax.set_aspect(1 / np.cos(np.radians(32.5)))
    ax.legend(loc="lower left", frameon=True, framealpha=0.9, edgecolor="none", fontsize=7.5); ax.grid(False)
    ax.set_title("Iranian dams and medium-range missile launch bases")
    style.save(fig, "fig1_map"); plt.close(fig)

    # Fig 2: null distributions of the median NN distance
    obs = np.median(bases.d_dam)
    labels = {"CSR": "Uniform random in Iran (CSR)", "M1": "Matched: terrain", "M2": "Matched: terrain + city",
              "M3": "Matched: terrain + city + river", "RIV": "Dams re-placed along rivers"}
    fig, axes = plt.subplots(len(labels), 1, figsize=(6.5, 6.8), sharex=True)
    for ax, (m, lab) in zip(axes, labels.items()):
        v = nulls[m]
        ax.hist(v, bins=60, color=style.STEEL, alpha=0.55, edgecolor="white", linewidth=0.3)
        ax.axvline(obs, color=style.CRIMSON, lw=2)
        ax.text(0.99, 0.82, f"{lab}\nnull median {np.median(v):.1f} km, p = {res['tests'][m]['p_one_sided']:.3f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=8, color=style.INK,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
        ax.set_yticks([]); ax.grid(axis="y", visible=False)
    axes[0].text(obs - 1.5, axes[0].get_ylim()[1] * 0.95, f"observed {obs:.1f} km", color=style.CRIMSON, fontsize=8, va="top", ha="right")
    axes[-1].set_xlabel("Median distance from the 25 launch bases to their nearest dam (km)")
    fig.suptitle("Median base-to-dam distance: observed value and null distributions", fontsize=10, y=0.995)
    fig.tight_layout(); style.save(fig, "fig2_nulls"); plt.close(fig)

    # Fig 3: ECDF with envelopes
    fig, ax = plt.subplots(figsize=(6.5, 4))
    x = np.sort(bases.d_dam.values); y = np.arange(1, len(x) + 1) / len(x)
    q = np.linspace(0, 1, len(x) + 1)[1:]
    for m, col, lab in (("CSR", style.BLACK, "CSR 95% envelope"), ("M3", style.STEEL, "Matched (M3) 95% envelope")):
        c = curves[m]
        lo, hi, md = np.quantile(c, 0.025, axis=0), np.quantile(c, 0.975, axis=0), np.median(c, axis=0)
        ax.fill_betweenx(q, lo, hi, step="post", color=col, alpha=0.15 if m == "CSR" else 0.25, lw=0, label=lab)
        ax.step(md, q, where="post", color=col, lw=1.2, ls="--")
    ax.step(x, y, where="post", color=style.CRIMSON, lw=2, label="Observed launch bases")
    ax.set_xlabel("Distance to nearest dam (km)"); ax.set_ylabel("Cumulative share of bases")
    ax.set_xlim(0, max(80, x.max() + 5)); ax.legend(loc="lower right")
    ax.set_title("Distance to nearest dam: launch bases and null envelopes")
    style.save(fig, "fig3_ecdf"); plt.close(fig)

    # Fig 4: placebo
    rows = [("Missile launch bases (n = 25)", res["observed"]["median"], res["tests"]["CSR"]["null_median_of_medians"], res["tests"]["M3"]["null_median_of_medians"])]
    short = {"Cities >= 50k (Natural Earth)": "Towns of 50,000+", "Airports (Global Map Iran)": "Airports"}
    for k, v in res["placebo"].items():
        rows.append((f"{short.get(k, k)} (n = {v['n']})", v["observed_median"], v["csr_null_median"], v["m3_null_median"]))
    fig, ax = plt.subplots(figsize=(6.5, 3.1))
    for i, (lab, o, c, m3) in enumerate(rows):
        ax.hlines(i, 30, 66, color=style.GRID, lw=1, zorder=0)
        ax.scatter(c, i, s=55, marker="s", color=style.BLACK, zorder=2, label="Expected: random sites in Iran (CSR)" if i == 0 else None)
        ax.scatter(m3, i, s=70, marker="D", facecolor="none", edgecolor=style.STEEL, lw=1.8, zorder=3, label="Expected: matched sites (M3)" if i == 0 else None)
        ax.scatter(o, i, s=55, color=style.CRIMSON, zorder=4, label="Observed" if i == 0 else None)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xlim(30, 66); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Median distance to nearest dam (km)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=3, fontsize=7.5, handletextpad=0.4, columnspacing=1.2)
    ax.set_title("Placebo comparison: median distance to nearest dam")
    style.save(fig, "fig4_placebo"); plt.close(fig)

if __name__ == "__main__":
    run()
