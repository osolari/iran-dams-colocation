#!/usr/bin/env bash
# Reproduce every number, table and figure, then build the report.
set -euo pipefail
cd "$(dirname "$0")/src"
python3 prepare.py
python3 iran_analysis.py
python3 crosscountry.py
python3 global_bases.py
python3 make_tex.py
cd ../report && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
