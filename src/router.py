"""Routing helpers for shortest-path queries."""

from __future__ import annotations

import networkx as nx


def map_building_to_nearest_node(_graph: nx.Graph, _latitude: float, _longitude: float) -> int:
    """Map a building coordinate to nearest node.

    TODO(issue): Implement with OSMnx nearest nodes.
    """
    raise NotImplementedError("Nearest-node mapping is not implemented yet.")


def find_shortest_path(
    graph: nx.Graph,
    origin_node: int,
    destination_node: int,
    weight: str = "distance_m",
) -> tuple[list[int], float]:
    """Find shortest path and total distance."""
    
    try:
        path = nx.shortest_path(graph, source=origin_node, target=destination_node, weight=weight)
        distance = nx.path_weight(graph, path, weight=weight)
        return path, float(distance)

    except nx.NetworkXNoPath as e:
        raise ValueError(
            f"No route found between node {origin_node} and node {destination_node}"
        ) from e