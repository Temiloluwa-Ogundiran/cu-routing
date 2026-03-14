"""CSV export helpers for routing artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd


def export_dataframe(df: pd.DataFrame, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def _normalise_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_buildings_csv(buildings_df: pd.DataFrame, output_dir: str | Path) -> Path:
    output_path = _normalise_output_dir(output_dir) / "buildings.csv"
    export_dataframe(buildings_df, str(output_path))
    return output_path


def graph_to_edges_dataframe(graph: nx.MultiDiGraph, travel_mode: str = "walk") -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for source, target, key, edge_data in graph.edges(keys=True, data=True):
        distance = edge_data.get("distance_m", edge_data.get("length"))
        if distance is None:
            raise ValueError(f"Edge {source}->{target} key={key} has no distance_m or length.")
        records.append(
            {
                "edge_id": f"{source}-{target}-{key}",
                "from_node": source,
                "to_node": target,
                "distance_m": float(distance),
                "travel_mode": travel_mode,
                "surface": edge_data.get("surface"),
                "one_way": bool(edge_data.get("oneway", False)),
            }
        )
    return pd.DataFrame(records)


def export_graph_edges_csv(graph: nx.MultiDiGraph, output_dir: str | Path, travel_mode: str = "walk") -> Path:
    edges_df = graph_to_edges_dataframe(graph, travel_mode=travel_mode)
    output_path = _normalise_output_dir(output_dir) / "graph_edges.csv"
    export_dataframe(edges_df, str(output_path))
    return output_path


def export_routes_csv(routes_df: pd.DataFrame, output_dir: str | Path) -> Path:
    output_path = _normalise_output_dir(output_dir) / "routes.csv"
    export_dataframe(routes_df, str(output_path))
    return output_path


def write_validation_summary(
    *,
    output_dir: str | Path,
    buildings_count: int,
    graph_edges_count: int,
    routes_count: int,
) -> Path:
    timestamp = datetime.now(timezone.utc).isoformat()
    report = (
        "# Validation Summary\n\n"
        f"- Generated at: {timestamp}\n"
        f"- Buildings: {buildings_count}\n"
        f"- Graph edges: {graph_edges_count}\n"
        f"- Routes: {routes_count}\n"
    )

    output_path = _normalise_output_dir(output_dir) / "validation_summary.md"
    output_path.write_text(report, encoding="utf-8")
    return output_path
