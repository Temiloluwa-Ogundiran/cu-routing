# Tests for routing helpers.

from __future__ import annotations

import math

import networkx as nx
import pytest

from src.router import map_building_to_nearest_node

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