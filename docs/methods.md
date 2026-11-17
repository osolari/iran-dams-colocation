# Methods

## Co-location test

For each of the 25 launch bases, the great-circle distance to the nearest dam is computed. The 25 distances are
summarised by their median (primary statistic), their mean and the share within 20 km. Each statistic is compared with
10,000 draws from a sequence of null models of increasing stringency:

| Null | Comparison sites |
|---|---|
| CSR | Uniformly random locations in Iran (cells weighted by area). The comparison implicit in a visual reading of two maps. |
| M1 | For each base, a random location among the 40 grid cells closest to it in elevation and local relief. |
| M2 | As M1, additionally matched on distance to the nearest town of at least 50,000. |
| M3 | As M2, additionally matched on distance to the nearest mapped river. |
| RIV | Bases fixed; the dams are relocated at random along Iran's river network. |

Matching is nearest-neighbour in standardised covariate space on a 10 arc-minute grid; sampled locations are jittered
uniformly within their cell. All p-values are one-sided and test whether the bases are closer to dams than expected.
Placebo point sets (towns, airports) are run through the same CSR and M3 tests. Sensitivity is assessed across match
sizes k = 20, 40, 80 and three statistics.

## Global comparison

All current military sites in Wikidata with coordinates (instances of military base, Q245016, or any subclass, excluding
police barracks and dissolved sites) are assigned to states by point-in-polygon. For each site the distance to the
nearest dam (Global Dam Watch) and to the sea coast (Natural Earth 1:10m) is computed. States with at least 15 sites are
ranked by median and mean distance with 95% bootstrap intervals; dependent territories are excluded. The ratio of the
median distance for military sites to the median for 2,000 random points in the same state controls for each state's
geography and for country-specific gaps in dam coverage.

## Dam construction

Dam densities use national counts; construction timelines use Global Dam Watch completion years.

## Author catalogue

Articles were collected from Muck Rack, Context (Thomson Reuters Foundation), The Conversation and other outlets and
coded from headline and summary. See [The authors' record](authors.md).
