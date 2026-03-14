"""CLI entrypoint for the CU routing pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import (
    DEFAULT_BOUNDARY_GEOJSON_PATH,
    DEFAULT_BUILDINGS_CSV_PATH,
    DEFAULT_WALKING_SPEED_M_PER_MIN,
    PROCESSED_DATA_DIR,
)
from src.data_collection import load_buildings_csv
from src.export_csv import (
    export_buildings_csv,
    export_graph_edges_csv,
    export_routes_csv,
    write_validation_summary,
)
from src.graph_builder import build_walking_graph_from_polygon
from src.router import compute_all_pairs_routes, map_buildings_to_nodes


def run_pipeline(
    *,
    buildings_csv_path: str | Path,
    boundary_geojson_path: str | Path,
    output_dir: str | Path,
    algorithm: str,
    walking_speed_m_per_min: float,
) -> dict[str, Path]:
    buildings_df = load_buildings_csv(str(buildings_csv_path))
    if buildings_df.empty:
        raise ValueError("No buildings were loaded. Provide at least one building row.")

    graph = build_walking_graph_from_polygon(str(boundary_geojson_path))
    building_nodes_df = map_buildings_to_nodes(graph, buildings_df)
    routes_df = compute_all_pairs_routes(
        graph,
        building_nodes_df,
        algorithm=algorithm,
        walking_speed_m_per_min=walking_speed_m_per_min,
    )

    buildings_csv = export_buildings_csv(buildings_df, output_dir)
    graph_edges_csv = export_graph_edges_csv(graph, output_dir)
    routes_csv = export_routes_csv(routes_df, output_dir)
    validation_summary = write_validation_summary(
        output_dir=output_dir,
        buildings_count=len(buildings_df),
        graph_edges_count=graph.number_of_edges(),
        routes_count=len(routes_df),
    )

    return {
        "buildings_csv": buildings_csv,
        "graph_edges_csv": graph_edges_csv,
        "routes_csv": routes_csv,
        "validation_summary": validation_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Covenant University routing pipeline.")
    parser.add_argument(
        "--buildings-csv",
        default=str(DEFAULT_BUILDINGS_CSV_PATH),
        help="Input CSV containing building_name, latitude, longitude.",
    )
    parser.add_argument(
        "--boundary-geojson",
        default=str(DEFAULT_BOUNDARY_GEOJSON_PATH),
        help="Campus boundary GeoJSON path (Polygon or MultiPolygon).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROCESSED_DATA_DIR),
        help="Directory where buildings.csv, graph_edges.csv, routes.csv are written.",
    )
    parser.add_argument(
        "--algorithm",
        default="dijkstra",
        choices=("dijkstra", "astar"),
        help="Shortest-path algorithm to use.",
    )
    parser.add_argument(
        "--walking-speed-m-per-min",
        default=DEFAULT_WALKING_SPEED_M_PER_MIN,
        type=float,
        help="Walking speed used to estimate travel time in minutes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    outputs = run_pipeline(
        buildings_csv_path=args.buildings_csv,
        boundary_geojson_path=args.boundary_geojson,
        output_dir=args.output_dir,
        algorithm=args.algorithm,
        walking_speed_m_per_min=args.walking_speed_m_per_min,
    )

    for label, output_path in outputs.items():
        print(f"{label}: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
