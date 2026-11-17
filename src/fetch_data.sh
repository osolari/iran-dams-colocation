#!/usr/bin/env bash
# Re-download the public inputs. Run from the repository root. GDW must be fetched manually (see docs/sources.md).
set -euo pipefail
RAW=data/raw
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
for f in ne_10m_admin_0_countries ne_10m_coastline ne_10m_populated_places_simple ne_10m_airports; do
  curl -sSL -o "$RAW/$f.geojson" "$NE/$f.geojson"
done
curl -sSL -o "$RAW/earth-topography-10arcmin.nc" \
  https://github.com/fatiando-data/earth-topography-10arcmin/releases/download/v1/earth-topography-10arcmin.nc
mkdir -p "$RAW/globalmap_iran"
for l in miscp_irn inwatera_irn riverl_irn polbnda_irn builtupp_irn airp_irn; do
  for e in shp shx dbf prj; do
    curl -sSL -o "$RAW/globalmap_iran/$l.$e" "https://raw.githubusercontent.com/globalmaps/gmir20/master/$l.$e"
  done
done
mkdir -p "$RAW/wikidata"
Q='SELECT ?item ?itemLabel ?cls ?iso3 ?coord ?dissolved WHERE { VALUES ?root {wd:Q245016} ?item wdt:P31 ?cls . ?cls wdt:P279* ?root . ?item p:P625/psv:P625 ?cn . ?cn wikibase:geoLatitude ?lat ; wikibase:geoLongitude ?lon ; wikibase:geoGlobe wd:Q2 . BIND(CONCAT(STR(?lon)," ",STR(?lat)) AS ?coord) ?item wdt:P17 ?country . ?country wdt:P298 ?iso3 . OPTIONAL { ?item wdt:P576 ?dissolved } SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }'
curl -s -G https://query.wikidata.org/sparql --data-urlencode "query=$Q" -H "Accept: text/csv" \
  -A "iran-dams-colocation/0.1 (research)" -o "$RAW/wikidata/wikidata_military_bases_raw.csv"
date -u +%FT%TZ > "$RAW/wikidata/retrieved_utc.txt"
echo "Done. Place GDW_v1_0_shp/ under data/external/ to rebuild data/processed/gdw_barriers_global.csv."
