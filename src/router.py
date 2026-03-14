"""Routing helpers for shortest-path queries."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

import networkx as nx
import pandas as pd


def map_building_to_nearest_node(_graph: nx.Graph, _latitude: float, _longitude: float) -> int:
    """Map a building coordinate to nearest node.

    TODO(issue): Implement with OSMnx nearest nodes.
    """
    if len(_graph) == 0:
        raise ValueError(
            "Cannot map a coordinate to a node: the graph has no nodes. "
            "Please ensure the graph is properly loaded with building nodes."
        )
    nearest_node: int | None = None
    min_distance = math.inf
    for node_id, data in _graph.nodes(data=True):
        node_lat: float = data["y"]     # raises KeyError if missing
        mode_long: float = data["x"]    # raises KeyError if missing

        distance = math.hypot(_latitude - node_lat, _longitude - mode_long)
        if distance < min_distance:
            min_distance = distance
            nearest_node = node_id
    return int(nearest_node)    


def map_buildings_to_nodes(graph: nx.Graph, buildings_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"building_id", "building_name", "latitude", "longitude"}
    missing = required_columns.difference(buildings_df.columns)
    if missing:
        raise ValueError(f"Missing required building columns: {sorted(missing)}")

    records: list[dict[str, Any]] = []
    for row in buildings_df.itertuples(index=False):
        node_id = map_building_to_nearest_node(graph, float(row.latitude), float(row.longitude))
        records.append(
            {
                "building_id": row.building_id,
                "building_name": row.building_name,
                "node_id": int(node_id),
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
            }
        )
    return pd.DataFrame(records)


def _astar_heuristic(graph: nx.Graph, node_a: int, node_b: int) -> float:
    data_a = graph.nodes[node_a]
    data_b = graph.nodes[node_b]
    if "y" not in data_a or "x" not in data_a or "y" not in data_b or "x" not in data_b:
        return 0.0
    return math.hypot(float(data_a["y"]) - float(data_b["y"]), float(data_a["x"]) - float(data_b["x"]))


def find_shortest_path(
    graph: nx.Graph,
    origin_node: int,
    destination_node: int,
    weight: str = "distance_m",
    algorithm: str = "dijkstra",
) -> tuple[list[int], float]:
    """Find shortest path and total distance in meters."""
    if origin_node not in graph:
        raise ValueError(f"Origin node {origin_node} not found in graph.")
    if destination_node not in graph:
        raise ValueError(f"Destination node {destination_node} not found in graph.")

    if origin_node == destination_node:
        return [int(origin_node)], 0.0

    normalised_algorithm = algorithm.lower().strip()
    if normalised_algorithm not in {"dijkstra", "astar"}:
        raise ValueError(f"Unsupported routing algorithm: {algorithm}")

    try:
        if normalised_algorithm == "astar":
            path = nx.astar_path(
                graph,
                source=origin_node,
                target=destination_node,
                heuristic=lambda a, b: _astar_heuristic(graph, a, b),
                weight=weight,
            )
        else:
            path = nx.shortest_path(graph, source=origin_node, target=destination_node, weight=weight)
    except nx.NetworkXNoPath as exc:
        raise ValueError(f"No route found between nodes {origin_node} and {destination_node}.") from exc

    distance = nx.path_weight(graph, path, weight=weight)
    return path, float(distance)


def compute_all_pairs_routes(
    graph: nx.Graph,
    building_nodes_df: pd.DataFrame,
    *,
    algorithm: str = "dijkstra",
    weight: str = "distance_m",
    walking_speed_m_per_min: float = 80.0,
) -> pd.DataFrame:
    required_columns = {"building_id", "building_name", "node_id"}
    missing = required_columns.difference(building_nodes_df.columns)
    if missing:
        raise ValueError(f"Missing required building-node columns: {sorted(missing)}")
    if walking_speed_m_per_min <= 0:
        raise ValueError("walking_speed_m_per_min must be positive.")

    computed_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []

    for origin in building_nodes_df.itertuples(index=False):
        for destination in building_nodes_df.itertuples(index=False):
            if origin.building_id == destination.building_id:
                continue

            try:
                path, distance_m = find_shortest_path(
                    graph,
                    int(origin.node_id),
                    int(destination.node_id),
                    weight=weight,
                    algorithm=algorithm,
                )
            except ValueError:
                # Skip unreachable pairs and keep route table focused on valid routes.
                continue

            estimated_time_min = distance_m / walking_speed_m_per_min
            records.append(
                {
                    "origin_building_id": origin.building_id,
                    "destination_building_id": destination.building_id,
                    "algorithm": algorithm.lower().strip(),
                    "distance_m": float(distance_m),
                    "estimated_time_min": float(estimated_time_min),
                    "path_node_count": len(path),
                    "path_nodes": "|".join(str(node_id) for node_id in path),
                    "path_buildings": f"{origin.building_name}|{destination.building_name}",
                    "computed_at": computed_at,
                }
            )

    routes_df = pd.DataFrame(records)
    if routes_df.empty:
        return pd.DataFrame(
            columns=[
                "origin_building_id",
                "destination_building_id",
                "algorithm",
                "distance_m",
                "estimated_time_min",
                "path_node_count",
                "path_nodes",
                "path_buildings",
                "computed_at",
            ]
        )
    return routes_df.sort_values(["origin_building_id", "destination_building_id"]).reset_index(drop=True)
