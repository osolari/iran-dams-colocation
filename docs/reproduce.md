# Reproduce

```bash
git clone git@github.com:osolari/iran-dams-colocation.git
cd iran-dams-colocation
pip install -r requirements.txt
bash src/fetch_data.sh   # optional: refresh public inputs (Global Dam Watch must be fetched manually)
./run_all.sh             # data preparation, analyses, figures, LaTeX tables, report PDF, site pages
```

The random seed is fixed (`SEED = 20261116` in `src/common.py`); a full run takes about two minutes.

## Documentation site

```bash
pip install -r requirements-docs.txt   # MkDocs pinned below 2.0
mkdocs serve        # local preview at http://127.0.0.1:8000
mkdocs gh-deploy    # build and push to the gh-pages branch
```

The GitHub Actions workflow in `.github/workflows/docs.yml` rebuilds and publishes the site on every push to `main`.

## Repository layout

| Path | Contents |
|---|---|
| `data/raw/` | Inputs as downloaded |
| `data/processed/` | Derived datasets |
| `src/` | Analysis code |
| `results/tables/` | CSV and JSON outputs |
| `report/` | LaTeX report, figures (PDF), generated macros and tables |
| `docs/` | This site: pages, figures (PNG), data sources |
