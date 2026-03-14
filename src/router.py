"""Routing helpers for shortest-path queries."""

from __future__ import annotations
import math

import networkx as nx


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


def find_shortest_path(
    graph: nx.Graph,
    origin_node: int,
    destination_node: int,
    weight: str = "distance_m",
) -> tuple[list[int], float]:
    """Find shortest path and total distance.

    TODO(issue): Add richer error handling and routing metadata.
    """
    path = nx.shortest_path(graph, source=origin_node, target=destination_node, weight=weight)
    distance = nx.path_weight(graph, path, weight=weight)
    return path, float(distance)
