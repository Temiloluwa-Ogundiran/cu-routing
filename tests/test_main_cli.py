from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pandas as pd
import pytest

import main


def _write_buildings_csv(path: Path) -> None:
    path.write_text(
        """building_name,latitude,longitude
Alpha Hall,6.6700,3.1500
Beta Hall,6.6710,3.1510
Gamma Hall,6.6720,3.1520
""",
        encoding="utf-8",
    )


def _write_boundary_geojson(path: Path) -> None:
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[3.149, 6.669], [3.153, 6.669], [3.153, 6.673], [3.149, 6.673], [3.149, 6.669]]],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.add_node(1, y=6.6700, x=3.1500)
    graph.add_node(2, y=6.6710, x=3.1510)
    graph.add_node(3, y=6.6720, x=3.1520)
    graph.add_edge(1, 2, key=0, distance_m=100.0)
    graph.add_edge(2, 1, key=0, distance_m=100.0)
    graph.add_edge(2, 3, key=0, distance_m=80.0)
    graph.add_edge(3, 2, key=0, distance_m=80.0)
    graph.add_edge(1, 3, key=0, distance_m=250.0)
    graph.add_edge(3, 1, key=0, distance_m=250.0)
    return graph


def test_run_pipeline_writes_outputs(tmp_path, monkeypatch):
    buildings_csv = tmp_path / "buildings.csv"
    boundary_geojson = tmp_path / "boundary.geojson"
    output_dir = tmp_path / "processed"
    _write_buildings_csv(buildings_csv)
    _write_boundary_geojson(boundary_geojson)

    monkeypatch.setattr(main, "build_walking_graph_from_polygon", lambda _path: _graph())

    result = main.run_pipeline(
        buildings_csv_path=buildings_csv,
        boundary_geojson_path=boundary_geojson,
        output_dir=output_dir,
        algorithm="dijkstra",
        walking_speed_m_per_min=80.0,
    )

    assert set(result.keys()) == {"buildings_csv", "graph_edges_csv", "routes_csv", "validation_summary"}
    assert result["buildings_csv"].exists()
    assert result["graph_edges_csv"].exists()
    assert result["routes_csv"].exists()
    assert result["validation_summary"].exists()

    routes_df = pd.read_csv(result["routes_csv"])
    assert len(routes_df) == 6


def test_main_cli_runs_successfully(tmp_path, monkeypatch):
    buildings_csv = tmp_path / "buildings.csv"
    boundary_geojson = tmp_path / "boundary.geojson"
    output_dir = tmp_path / "processed"
    _write_buildings_csv(buildings_csv)
    _write_boundary_geojson(boundary_geojson)

    monkeypatch.setattr(main, "build_walking_graph_from_polygon", lambda _path: _graph())

    exit_code = main.main(
        [
            "--buildings-csv",
            str(buildings_csv),
            "--boundary-geojson",
            str(boundary_geojson),
            "--output-dir",
            str(output_dir),
            "--algorithm",
            "dijkstra",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "buildings.csv").exists()
    assert (output_dir / "graph_edges.csv").exists()
    assert (output_dir / "routes.csv").exists()


def test_main_cli_help_exits_cleanly():
    with pytest.raises(SystemExit) as exc:
        main.main(["--help"])
    assert exc.value.code == 0
