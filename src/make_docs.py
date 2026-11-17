"""Generate the documentation-site pages that carry numbers (index, results) from results files."""
from __future__ import annotations

import json
import shutil
import pandas as pd

from common import ROOT, TAB

DOCS = ROOT / "docs"
r = json.load(open(TAB / "iran_results.json"))
g = json.load(open(TAB / "global_ranking_summary.json"))
tl = json.load(open(TAB / "dam_timelines_gdw.json"))
dens = pd.read_csv(TAB / "dam_density_official.csv")
sens = pd.read_csv(TAB / "iran_sensitivity.csv")


def p(x):
    return "< 0.001" if x < 0.001 else f"{x:.3f}"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


o, t = r["observed"], r["tests"]
w, wr = g["iran_alma_d_water_rank_among"], g["iran_alma_d_water_ratio_rank"]
dr = g["iran_alma_d_dam_ratio_rank"]
d = dens.set_index("country").dams_per_10k_km2

index = f"""# A Statistical Assessment of "War May Answer Longtime Riddle of Iranian Dams Built for No Clear Reason"

*The New York Times*, 16 November 2026

Omid S. Solari, Ph.D. (Ph.D. in Statistics, University of California, Berkeley; sAIm Labs)

On 16 November 2026 *The New York Times* suggested that Iran's dams overlap geographically with the underground missile
sites struck by the United States and Israel, that Iran has an unusually large number of dams, and that the dams may have
been built to supply those sites. This site documents an open, reproducible test of each element of that argument.

**The data do not support the claim.** Missile bases are not unusually close to dams, military bases near water are the
norm worldwide, and Iran's dam numbers are not unusual for a water-scarce country.

[Read the full report (PDF)](report.pdf){{ .md-button .md-button--primary }}
[Source code on GitHub](https://github.com/osolari/iran-dams-colocation){{ .md-button }}

![Iranian dams and launch bases](figures/fig1_map.png)

## Findings

| Claim in the article | What the data show |
|---|---|
| Dams and missile sites overlap | **Rejected. Not significant against random locations in Iran (median {o['median']:.1f} km, p = {p(t['CSR']['p_one_sided'])}); after matching on terrain, towns and rivers the bases lie farther from dams than expected (p = {p(t['M3']['p_one_sided'])}).** The mean is shorter than random (p = {p(sens.query("null=='CSR' and statistic=='mean'").p_one_sided.iloc[0])}) but not after matching. |
| The overlap is distinctive to military sites | **Rejected. Towns and airports show the same apparent overlap**; it reflects settlement geography. |
| Military siting near water is anomalous | **Rejected. Iran's launch bases rank {ordinal(w['rank'])} of {w['of']} states for proximity to the nearest dam or coast; military sites in {round(100*w['share_of_countries_closer'])}% of states lie closer to water.** Relative to each state's own geography: {ordinal(dr['rank'])} for dams, {ordinal(wr['rank'])} for dams or coast. |
| Iran has unusually many dams | **Rejected. Dam density of {d['Iran']:.1f} per 10,000 km², below Spain ({d['Spain']:.1f}), Turkey ({d['Turkey']:.1f}) and Morocco ({d['Morocco']:.1f}); construction peaks in {tl['Iran']['peak_5yr']}–{tl['Iran']['peak_5yr']+4}, the same period as Turkey.** |

## Caveats

The article's full text, Nima Shokri's map of 533 dams and the article's strike map are not public. Global Dam Watch
(183 Iranian dams) and the Alma Research Center's list of 25 launch bases are used instead. See
[Data sources](sources.md) and the limitations section of the report.
"""
(DOCS / "index.md").write_text(index)

nulls = "\n".join(
    f"| {k} | {v['null_median_of_medians']:.1f} | [{v['null_q025']:.1f}, {v['null_q975']:.1f}] | {v['ratio_obs_to_null']:.2f} | {p(v['p_one_sided'])} |"
    for k, v in t.items())
sv = r["struck_vs_not"]; pl = r["placebo"]
cities = pl["Cities >= 50k (Natural Earth)"]; air = pl["Airports (Global Map Iran)"]
rank = pd.read_csv(TAB / "country_ranking_current.csv")
alma = g["iran_alma"]
rank = pd.concat([rank, pd.DataFrame([{**alma, "country": "**Iran: launch bases (Alma)**"}])], ignore_index=True)
rank = rank.sort_values("d_water_median").reset_index(drop=True)
rank_tab = "\n".join(
    f"| {i+1} | {x.country if not str(x.country).startswith('Iran') else '**' + str(x.country).strip('*') + '**'} | {int(x.n_bases)} | "
    f"{x.d_water_median:.1f} | {x.d_water_mean:.1f} | {x.d_dam_median:.1f} | {x.d_coast_median:.1f} | {x.d_water_ratio:.2f} |"
    for i, x in rank.iterrows())

results = f"""# Results

## 1. Co-location of launch bases and dams

Observed median distance from the {r['n_bases']} launch bases to their nearest dam: **{o['median']:.1f} km**
(mean {o['mean']:.1f} km; {100*o['share_le10']:.0f}% within 10 km, {100*o['share_le20']:.0f}% within 20 km).

| Null model | Expected median (km) | 95% range | Observed / expected | p (one-sided) |
|---|---|---|---|---|
{nulls}

![Null distributions](figures/fig2_nulls.png)

![ECDF with envelopes](figures/fig3_ecdf.png)

### Placebo sites

| Site set | n | Observed median (km) | p, random sites | p, matched sites |
|---|---|---|---|---|
| Missile launch bases | {r['n_bases']} | {o['median']:.1f} | {p(t['CSR']['p_one_sided'])} | {p(t['M3']['p_one_sided'])} |
| Towns of 50,000+ | {cities['n']} | {cities['observed_median']:.1f} | {p(cities['p_csr'])} | {p(cities['p_m3'])} |
| Airports | {air['n']} | {air['observed_median']:.1f} | {p(air['p_csr'])} | {p(air['p_m3'])} |

![Placebo comparison](figures/fig4_placebo.png)

### Robustness

- Large dams only ({r['n_large_dams']}): CSR p = {p(r['tests_large']['CSR']['p'])}; M3 p = {p(r['tests_large']['M3']['p'])}.
- Struck in June 2025 against not attacked: medians {sv['median_struck']:.1f} and {sv['median_not']:.1f} km, Mann–Whitney p = {sv['mannwhitney_p']:.2f}.
- Sensitivity to statistic and match size: `results/tables/iran_sensitivity.csv`.

## 2. Military installations and water worldwide

![Ranking by distance to dam or coast](figures/fig7_rank_water.png)

![Ranking by distance to dam](figures/fig8_rank_dam.png)

| Rank | State | n | Water median | Water mean | Dam median | Coast median | Ratio |
|---|---|---|---|---|---|---|---|
{rank_tab}

Distances in km. Water = nearest dam or sea coast. Ratio = median for military sites divided by median for random points
in the same state.

## 3. Dam construction under water scarcity

![Dam completions](figures/fig5_timelines.png)

![Dam density](figures/fig6_density.png)
"""
(DOCS / "results.md").write_text(results)

shutil.copy(ROOT / "report" / "main.pdf", DOCS / "report.pdf")
print("docs written")
