from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd

from src import export_csv


def test_export_buildings_csv_writes_expected_file(tmp_path):
    buildings_df = pd.DataFrame(
        [
            {"building_id": "alpha", "building_name": "Alpha Hall", "latitude": 6.67, "longitude": 3.15},
            {"building_id": "beta", "building_name": "Beta Hall", "latitude": 6.68, "longitude": 3.16},
        ]
    )

    output_path = export_csv.export_buildings_csv(buildings_df, tmp_path)

    assert output_path == tmp_path / "buildings.csv"
    assert output_path.exists()
    written = pd.read_csv(output_path)
    assert list(written.columns) == list(buildings_df.columns)


def test_graph_to_edges_dataframe_extracts_core_columns():
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, distance_m=12.5, oneway=True, surface="paved")
    graph.add_edge(2, 3, key=1, length=7.0, oneway=False)

    edges_df = export_csv.graph_to_edges_dataframe(graph)

    assert len(edges_df) == 2
    assert set(edges_df.columns) == {
        "edge_id",
        "from_node",
        "to_node",
        "distance_m",
        "travel_mode",
        "surface",
        "one_way",
    }
    assert edges_df.loc[0, "distance_m"] == 12.5


def test_export_graph_edges_csv_writes_file(tmp_path):
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, distance_m=5.0)

    output_path = export_csv.export_graph_edges_csv(graph, tmp_path)

    assert output_path == tmp_path / "graph_edges.csv"
    assert output_path.exists()
    written = pd.read_csv(output_path)
    assert len(written) == 1
    assert set(written.columns) == {
        "edge_id",
        "from_node",
        "to_node",
        "distance_m",
        "travel_mode",
        "surface",
        "one_way",
    }


def test_export_routes_csv_writes_file(tmp_path):
    routes_df = pd.DataFrame(
        [
            {
                "origin_building_id": "alpha",
                "destination_building_id": "beta",
                "algorithm": "dijkstra",
                "distance_m": 120.0,
                "estimated_time_min": 1.5,
                "path_node_count": 4,
                "path_nodes": "1|2|3|4",
                "path_buildings": "Alpha Hall|Beta Hall",
                "computed_at": "2026-03-14T12:00:00+00:00",
            }
        ]
    )

    output_path = export_csv.export_routes_csv(routes_df, tmp_path)

    assert output_path == tmp_path / "routes.csv"
    assert output_path.exists()
    written = pd.read_csv(output_path)
    assert len(written) == 1
    assert set(written.columns) == set(routes_df.columns)


def test_write_validation_summary_creates_report(tmp_path):
    report_path = export_csv.write_validation_summary(
        output_dir=tmp_path,
        buildings_count=2,
        graph_edges_count=10,
        routes_count=3,
    )

    assert report_path == tmp_path / "validation_summary.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Buildings: 2" in content
    assert "Graph edges: 10" in content
    assert "Routes: 3" in content
