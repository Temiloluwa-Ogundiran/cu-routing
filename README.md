# CU Routing (Covenant University)

Team project for learning Git collaboration while building a data-science routing pipeline.

## What We Are Building
- Collect building coordinates for Covenant University (OpenStreetMap source).
- Build a walking network graph.
- Compute shortest paths for all building pairs.
- Export clean CSV outputs for analysis.

## Project Outputs
- `data/processed/buildings.csv`
- `data/processed/graph_edges.csv`
- `data/processed/routes.csv`
- `data/processed/validation_summary.md`

## Team Workflow (Beginner Friendly)
1. Fork this repo.
2. Pick an open issue and comment `/take` to claim it.
3. Create a branch in your fork.
4. Make only the requested change.
5. Open a PR to this repo.
6. Maintainers review and merge.

Read these first:
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [Git Beginner Guide](docs/guides/git-beginner-guide.md)
- [Project Design](design.md)
- [Output Schema](docs/output-schema.md)

## Quick Start
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

## Run Full Pipeline
```bash
python main.py
```

This uses default inputs:
- `data/manual/buildings_seed.csv`
- `data/manual/campus_boundary.geojson`

And writes:
- `data/processed/buildings.csv`
- `data/processed/graph_edges.csv`
- `data/processed/routes.csv`
- `data/processed/validation_summary.md`

### Custom Run Example
```bash
python main.py \
  --buildings-csv data/manual/buildings_seed.csv \
  --boundary-geojson data/manual/campus_boundary.geojson \
  --output-dir data/processed \
  --algorithm dijkstra \
  --walking-speed-m-per-min 80
```

## Troubleshooting
### `osmnx is required to build the campus walking graph`
Install dependencies again:
```bash
pip install -r requirements.txt
```

### `Boundary geometry is not a valid GeoJSON geometry`
Check `data/manual/campus_boundary.geojson`:
- geometry must be Polygon or MultiPolygon
- rings must be closed
- coordinates must be numeric (`lon, lat`)

### `No buildings were loaded`
Check `data/manual/buildings_seed.csv`:
- file must have headers: `building_name,latitude,longitude`
- at least one building row must exist

### `No route found between nodes ...`
This means the walking network is disconnected for some pairs.
- verify campus boundary covers all target buildings
- verify building coordinates are inside the boundary
- inspect generated `graph_edges.csv` for coverage

## Repository Structure
```text
src/                 # project code
tests/               # unit tests
data/manual/         # manual input files
data/processed/      # generated csv outputs
docs/guides/         # contributor onboarding guides
docs/output-schema.md# output CSV schema reference
design.md            # project design and routing approach
```
