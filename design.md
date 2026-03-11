# Covenant University Routing Design

**Objective**
Build a reproducible pipeline to:
1. collect Covenant University building coordinates,
2. compute shortest campus routes,
3. export routing outputs and supporting metadata to CSV.

**Scope**
- Routing target: building-to-building paths inside Covenant University, Ota, Ogun, Nigeria.
- Initial travel mode: walking only.
- Output format: CSV files for coordinates, graph edges, and route results.
- Route generation scope: all building pairs.

## Requirements
- Maintain an authoritative building list with coordinates and source provenance.
- Use a graph-based shortest path method (Dijkstra or A*).
- Support route queries between named buildings.
- Export results in machine-readable CSV for analysis and presentation.
- Provide repeatable scripts and validation checks.

### Approach : OpenStreetMap + OSMnx + NetworkX
- Use OSM road/path network and campus buildings from OSM.
- Build a weighted graph and map building points to nearest network nodes.
- Compute shortest paths with Dijkstra/A*.

- OpenStreetMap is the primary source for campus buildings and walk network.
- Missing buildings will be added via manual override CSV entries.

## Proposed Architecture
- `data/raw/`: downloaded raw map extracts and source snapshots.
- `data/processed/`: normalized building tables and graph export tables.
- `src/data_collection.py`: fetch and normalize building coordinates.
- `src/graph_builder.py`: create weighted campus graph from OSM network.
- `src/router.py`: shortest path computation utilities.
- `src/export_csv.py`: CSV exports for all deliverables.
- `tests/`: parser, graph, and routing correctness tests.

## Data Model

### `buildings.csv`
- `building_id` (string, stable slug)
- `building_name` (string)
- `latitude` (float)
- `longitude` (float)
- `category` (string, optional)
- `source` (string; `osm`, `manual`, `hybrid`)
- `source_ref` (string; URL or note)
- `last_verified_at` (ISO timestamp)

### `graph_edges.csv`
- `edge_id` (string)
- `from_node` (string/int)
- `to_node` (string/int)
- `distance_m` (float)
- `travel_mode` (string)
- `surface` (string, optional)
- `one_way` (bool)

### `routes.csv`
- `origin_building_id`
- `destination_building_id`
- `algorithm` (`dijkstra` or `astar`)
- `distance_m`
- `estimated_time_min` (assume configurable walking speed)
- `path_node_count`
- `path_nodes` (delimiter-separated list)
- `path_buildings` (delimiter-separated names, when matched)
- `computed_at`

## Processing Flow
1. Define campus boundary polygon.
2. Pull OSM path network for the boundary.
3. Build and simplify graph; compute edge distances.
4. Collect building coordinates; normalize IDs.
5. Attach buildings to nearest graph nodes.
6. Compute shortest paths for selected origin/destination pairs.
7. Export all result CSV files.
8. Run validation checks and summary stats.

## Validation and Quality Checks
- Coordinate sanity:
  - Latitude/longitude ranges valid.
  - No duplicate building IDs.
- Graph quality:
  - Connected component size meets threshold.
  - Edge distances are positive and plausible.
- Routing quality:
  - Known sample routes are non-empty and reasonable.
  - Symmetry checks for undirected walking edges where applicable.
- Output quality:
  - CSV schema validation.
  - Row counts and null checks.

## Risks and Mitigations
- Missing buildings in OSM:
  - Mitigation: manual override file `data/manual/building_overrides.csv`.
- Inaccurate campus boundary:
  - Mitigation: store and review boundary geometry explicitly.
- Poor path network detail:
  - Mitigation: add custom edges for known internal walkways.

## Success Criteria
- At least 95% of target buildings have verified coordinates.
- Shortest path query works for all selected route pairs.
- CSV outputs are complete, validated, and reproducible from scripts.
