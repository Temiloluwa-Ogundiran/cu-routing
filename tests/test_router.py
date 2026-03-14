# Tests for routing helpers.

from __future__ import annotations

import math

import networkx as nx
import pandas as pd
import pytest

from src.router import compute_all_pairs_routes, find_shortest_path, map_building_to_nearest_node

def make_graph(nodes: list[tuple[int, float, float]]) -> nx.Graph:
    """Build a minimal OSMnx-style graph from (node_id, lat, lon) triples."""
    g = nx.Graph()
    for node_id, lat, lon in nodes:
        g.add_node(node_id, y=lat, x=lon)
    return g

# Tests – empty graph
class TestEmptyGraph:
    def test_raises_value_error(self):
        g = nx.Graph()
        with pytest.raises(ValueError, match = "no nodes"):
            map_building_to_nearest_node(g, 0.0, 0.0)
    
    def test_error_message_is_descriptive(self):
        g = nx.Graph()
        with pytest.raises(ValueError) as exc_info:
            map_building_to_nearest_node(g, 1.23, 4.56)
        assert "no nodes" in str(exc_info.value).lower()

# Tests – single node graph
class TestSingleNode:
    def test_only_node_is_returned(self):
        g = make_graph([(42, 10.0, 20.0)])
        assert map_building_to_nearest_node(g, 10.0, 20.0) == 42

    def test_exact_coordinate_match(self):
        g = make_graph([(7, 51.5074, -0.1278)])
        result = map_building_to_nearest_node(g, 51.5074, -0.1278)
        assert result == 7
    
    def test_distance_coordinate_still_returns_only_node(self):
        g = make_graph([(99, 0.0, 0.0)])
        assert map_building_to_nearest_node(g, 99.0, 180.0) == 99

# Tests – multiple nodes
class TestMultipleNodes:
    #Each building should map exactly one valid, nearest node.
    def graph(self) -> nx.Graph:
        return make_graph([
            (1, 0.0, 0.0),
            (2, 1.0, 0.0),
            (3, 0.0, 1.0),
            (4, 1.0, 1.0),
        ])
    
    def test_returns_closest_node_origin(self):
        g = self.graph()
        assert map_building_to_nearest_node(g, 0.0, 0.0) == 1
    
    def test_returns_closest_node_top_right(self):
        g = self.graph()
        assert map_building_to_nearest_node(g, 1.0, 1.0) == 4
    
    def test_returns_closest_node_near_node2(self):
        g = self.graph()
        # (0.9, 0.1) is closest to node 2 at (1.0, 0.0)
        assert map_building_to_nearest_node(g, 0.9, 0.1) == 2

    def test_returns_closest_node_near_node3(self):
        g = self.graph()
        # (0.1, 0.9) is closest to node 3 at (0.0, 1.0)
        assert map_building_to_nearest_node(g, 0.1, 0.9) == 3

    def test_result_is_valid_node_id(self):
        g = self.graph()
        result = map_building_to_nearest_node(g, 0.4, 0.4)
        assert result in g.nodes

    def test_return_type_is_int(self):
        g = self.graph()
        result = map_building_to_nearest_node(g, 0.0, 0.0)
        assert isinstance(result, int)

    def test_large_node_id_preserved(self):
        g = make_graph([(123456789, 48.8566, 2.3522)])
        result = map_building_to_nearest_node(g, 48.8566, 2.3522)
        assert result == 123456789

    def test_negative_coordinates(self):
        g = make_graph([
            (10, -33.8688, 151.2093),   # Sydney
            (11, -36.8485, 174.7633),   # Auckland
        ])
        # Close to Sydney
        assert map_building_to_nearest_node(g, -33.9, 151.1) == 10
        # Close to Auckland
        assert map_building_to_nearest_node(g, -36.8, 174.8) == 11   

# Tests – missing node attributes
class TestMissingAttributes:
    def test_missing_y_raises_key_error(self):
        g = nx.Graph()
        g.add_node(1, x=0.0)  # no 'y'
        with pytest.raises(KeyError):
            map_building_to_nearest_node(g, 0.0, 0.0)

    def test_missing_x_raises_key_error(self):
        g = nx.Graph()
        g.add_node(1, y=0.0)  # no 'x'
        with pytest.raises(KeyError):
            map_building_to_nearest_node(g, 0.0, 0.0)


# Tests - shortest path
class TestShortestPath:
    def test_returns_path_and_distance(self):
        g = nx.Graph()
        g.add_edge(1, 2, distance_m=10.0)
        g.add_edge(2, 3, distance_m=5.0)

        path, distance = find_shortest_path(g, 1, 3)

        assert path == [1, 2, 3]
        assert distance == pytest.approx(15.0)

    def test_raises_when_origin_missing(self):
        g = nx.Graph()
        g.add_node(2)

        with pytest.raises(ValueError, match="Origin node .* not found"):
            find_shortest_path(g, 1, 2)

    def test_raises_when_destination_missing(self):
        g = nx.Graph()
        g.add_node(1)

        with pytest.raises(ValueError, match="Destination node .* not found"):
            find_shortest_path(g, 1, 2)

    def test_raises_when_no_route_exists(self):
        g = nx.Graph()
        g.add_edge(1, 2, distance_m=1.0)
        g.add_edge(3, 4, distance_m=1.0)

        with pytest.raises(ValueError, match="No route found"):
            find_shortest_path(g, 1, 4)

    def test_raises_for_unknown_algorithm(self):
        g = nx.Graph()
        g.add_edge(1, 2, distance_m=1.0)

        with pytest.raises(ValueError, match="Unsupported routing algorithm"):
            find_shortest_path(g, 1, 2, algorithm="bellman-ford")


# Tests - all-pairs computation
class TestAllPairsRouting:
    def _graph(self) -> nx.Graph:
        g = nx.Graph()
        g.add_edge(1, 2, distance_m=10.0)
        g.add_edge(2, 3, distance_m=5.0)
        g.add_edge(1, 3, distance_m=25.0)
        return g

    def _building_nodes(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"building_id": "alpha", "building_name": "Alpha Hall", "node_id": 1},
                {"building_id": "beta", "building_name": "Beta Hall", "node_id": 2},
                {"building_id": "gamma", "building_name": "Gamma Hall", "node_id": 3},
            ]
        )

    def test_compute_all_pairs_routes_returns_ordered_pairs(self):
        routes_df = compute_all_pairs_routes(self._graph(), self._building_nodes(), walking_speed_m_per_min=100.0)

        # 3 buildings -> 3 * 2 ordered origin/destination pairs
        assert len(routes_df) == 6
        assert set(routes_df.columns) >= {
            "origin_building_id",
            "destination_building_id",
            "algorithm",
            "distance_m",
            "estimated_time_min",
            "path_node_count",
            "path_nodes",
            "path_buildings",
            "computed_at",
        }
        assert not (routes_df["origin_building_id"] == routes_df["destination_building_id"]).any()

    def test_compute_all_pairs_routes_calculates_time_and_paths(self):
        routes_df = compute_all_pairs_routes(self._graph(), self._building_nodes(), walking_speed_m_per_min=100.0)
        alpha_to_gamma = routes_df[
            (routes_df["origin_building_id"] == "alpha") & (routes_df["destination_building_id"] == "gamma")
        ].iloc[0]

        assert alpha_to_gamma["distance_m"] == pytest.approx(15.0)
        assert alpha_to_gamma["estimated_time_min"] == pytest.approx(0.15)
        assert alpha_to_gamma["path_node_count"] == 3
        assert alpha_to_gamma["path_nodes"] == "1|2|3"

    def test_compute_all_pairs_routes_raises_on_missing_columns(self):
        bad_df = pd.DataFrame([{"building_id": "alpha", "node_id": 1}])

        with pytest.raises(ValueError, match="Missing required building-node columns"):
            compute_all_pairs_routes(self._graph(), bad_df)
