"""CLI entrypoint for the routing pipeline"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src import data_collection, graph_builder, router, export_csv

def parse_arguments():
    """Set up and parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="CU Routing Pipeline - Generate campus walking routes"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the buildings csv input file"
    )
    parser.add_argument(
        "--boundary", "-b",
        required=True,
        help="Path to campus boundary GeoJSON file"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for csv files (would be created if it does not exist)"
    )
    return parser.parse_args()

def validate_files_exist(buildings_path, boundary_path):
    """Check the existence of input files"""
    if not buildings_path.exists():
        print("Error: Buildings file does not exist")
        return False
    if not boundary_path.exists():
        print("Error: Boundary file does not exist")
        return False
    return True

def setup_output_dir(output_dir):
    """Sets up the output directory for csv outputs if given path not found"""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def process_buildings(buildings_path, output_dir):
    """Loads buildings and returns df of processed buildings"""
    buildings_df = data_collection.load_buildings_csv(str(buildings_path))
    buildings_output = output_dir / "buildings.csv"
    export_csv.export_dataframe(buildings_df, str(buildings_output))
    print(f"Saved {len(buildings_df)} buildings to {buildings_output}")
    return buildings_df

def build_graph(boundary_path, output_dir):
    """Build walking path graph and save edges to csv"""
    graph = graph_builder.build_walking_graph_from_polygon(str(boundary_path))
    if graph.number_of_nodes() == 0:
        print("Warning: Graph is empty (placeholder implementation)")
        edges_df = pd.DataFrame(columns=["from_node", "to_node", "distance_m"])
    else:
        print(f"graph built with {graph.number_of_nodes()} nodes")
        edges_data = []
        for u, v, data in graph.edges(data=True):
            edges_data.append({
                "from_node": u,
                "to_node": v,
                "distance_m": data.get("distance_m", data.get("length", 0))
            })
        edges_df = pd.DataFrame(edges_data)
    edges_output = output_dir / "graph_edges.csv"
    export_csv.export_dataframe(edges_df, str(edges_output))
    print(f"Saved {len(edges_df)} edges to {edges_output}")
    return graph

def calculate_routes(graph, buildings_df, output_dir, walking_speed_kmh=5):
    """Calculate routes for buildings and return a dataframe of routes
    NOTE: walking speed of 5 was assigned as a placeholder"""
    try:
        # Test if routing is possible
        test_node = router.map_building_to_nearest_node(
            graph,
            buildings_df.iloc[0]['latitude'],
            buildings_df.iloc[0]['longitude']
        )
        # Calculate ALL routes
        n_buildings = len(buildings_df)
        routes_data = []
        for i in range(n_buildings):
            for j in range(i+1, n_buildings):
                b1 = buildings_df.iloc[i]
                b2 = buildings_df.iloc[j]
                try:
                    node1 = router.map_building_to_nearest_node(graph, b1["latitude"], b1["longitude"])
                    node2 = router.map_building_to_nearest_node(graph, b2["latitude"], b2["longitude"])
                    path, distance = router.find_shortest_path(graph, node1, node2)
                    path_nodes_str = ";".join(str(node) for node in path)
                    estimated_time_min = (distance/1000) / (walking_speed_kmh/60)
                    # TODO: When building-to-node mapping is available
                    path_buildings_str = ""
                    routes_data.append({
                        "origin_building_id": b1["building_id"],
                        "destination_building_id": b2["building_id"],
                        "algorithm": "dijkstra",
                        "distance_m": round(distance, 2),
                        "estimated_time_min": round(estimated_time_min, 2),
                            "path_node_count": len(path),
                        "path_nodes": path_nodes_str,
                        "path_buildings": path_buildings_str,
                        "computed_at": pd.Timestamp.now().isoformat()
                    })
                except Exception as e:
                    print(f"Skipped building{b1['building_id']} -> building{b2['building_id']}: {e}")
                    continue
        routes_df = pd.DataFrame(routes_data)
        print(f"Successfully calculated {len(routes_df)} routes")
    except NotImplementedError:
        print("Nearest-node mapping not implemented")
        print("Creating routes.csv with correct schema but no data")
        routes_df = pd.DataFrame(columns=[
            'origin_building_id', 'destination_building_id',
            'algorithm', 'distance_m', 'estimated_time_min',
            'path_node_count', 'path_nodes', 'path_buildings',
            'computed_at'
        ])
    except Exception as e:
        print(f"Unexpected error: {e}")
        routes_df = pd.DataFrame(columns=[
            'origin_building_id', 'destination_building_id',
            'algorithm', 'distance_m', 'estimated_time_min',
            'path_node_count', 'path_nodes', 'path_buildings',
            'computed_at'
        ])
    routes_output = output_dir / "routes.csv"
    export_csv.export_dataframe(routes_df, str(routes_output))
    print(f"Saved {len(routes_df)} routes to {routes_output}")
    return routes_df

def main():
    """Main pipeline execution function - Orchestrates all steps"""
    args = parse_arguments()
    buildings_path = Path(args.input)
    boundary_path = Path(args.boundary)
    output_dir = Path(args.output)
    if not validate_files_exist(buildings_path, boundary_path):
        return 1
    setup_output_dir(output_dir)
    try:
        print("Processing buildings...")
        buildings_df = process_buildings(buildings_path, output_dir)
        print("Creating graph...")
        graph = build_graph(boundary_path, output_dir)
        print("Calculating routes...")
        routes_df = calculate_routes(graph, buildings_df, output_dir)
        print("Process Successful")
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
