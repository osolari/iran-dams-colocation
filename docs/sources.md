# Data sources and provenance

| File | What it is | Source | Licence |
|---|---|---|---|
| `data/processed/gdw_barriers_global.csv` | Slim copy of Global Dam Watch v1.0 barriers (41,145 worldwide) | Lehner et al. (2024), *Scientific Data* 11:1069, figshare doi:10.6084/m9.figshare.25988293 | CC BY 4.0 |
| `data/processed/iran_dams_gdw.csv` | GDW barriers inside Iran (183, incl. 2 border dams) | derived | CC BY 4.0 |
| `data/raw/grand_v13_dams.csv` | GRanD v1.3 attribute table (cross-check) | Lehner et al. (2011); mirrored at github.com/ghowoo/ghowoo.github.io | non-commercial |
| `data/raw/iran_missile_bases_alma_2026.csv` | 25 medium-range launch bases, coordinates, June 2025 strike status | Alma Research and Education Center, Jan 2026 (URL in report) | quoted for research |
| `data/raw/wikidata/wikidata_military_bases_raw.csv` | Wikidata items that are military bases (Q245016 and subclasses) with coordinates | query.wikidata.org, retrieved timestamp in `retrieved_utc.txt` | CC0 |
| `data/raw/earth-topography-10arcmin.nc` | ETOPO1 at 10 arc-minutes | Fatiando a Terra, doi:10.5281/zenodo.5882203 | CC BY |
| `data/raw/ne_10m_*.geojson` | Countries, coastline (incl. Caspian), populated places, airports | Natural Earth via github.com/nvkelso/natural-earth-vector | public domain |
| `data/raw/globalmap_iran/` | Iranian rivers, airports, settlements (Global Map Iran v2) | National Cartographic Center of Iran / ISCGM, github.com/globalmaps/gmir20 | non-commercial |
| `data/raw/official_dam_counts.csv` | National dam counts for density comparison | sources and URLs in the file | cited |

## Not available to this analysis
- The NYT article text (nytimes.com is blocked to the analysis tools; syndicated excerpts used instead).
- Nima Shokri's map of 533 Iranian dams (unpublished).
- The NYT's map of 2026 strikes on suspected missile sites (unpublished).
- OpenStreetMap military features via Overpass (host not reachable at run time); Wikidata used instead.

## Notes
- Alma lists one base as "Ahbar (ابهر)"; the Persian name is Abhar, used here.
- GDW is the full global shapefile (239 MB unzipped) and is not committed. Download `GDW_v1_0_shp.zip` from figshare and unzip into `data/external/` to rebuild from scratch; otherwise `prepare.py` uses the committed processed CSV.
