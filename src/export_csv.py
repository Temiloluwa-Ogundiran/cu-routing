"""CSV export helpers for routing artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

Building_Columns = [
    "building_id",
    "building_name",
    "latitude",
    "longitude",
    "category",
    "source",
    "source_ref",
    "last_verified_at",
]

graph_edges_columns = [
"edge_id",
"from_node",
"to_node",
"distance_m",
"travel_mode",
"surface",
"one_way",
]


def export_dataframe(df: pd.DataFrame, headers: list[str], output_path: str ) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, header=headers, encoding="utf-8")




df_buildings = pd.DataFrame({
    "building_id": ["b1", "b2"],
    "building_name": ["Library", "Lab"],
    "latitude": [6.5, 6.6],
    "longitude": [3.3, 3.4],
    "category": ["academic", "research"],
    "source": ["osm", "manual"],
    "source_ref": ["url1", "url2"],
    "last_verified_at": ["2026-03-11T12:00:00", "2026-03-11T12:30:00"]
})

df_graph = pd.DataFrame({
    "edge_id": ["e1", "e2"],
    "from_node": ["n1", "n2"],
    "to_node": ["n2", "n3"],
    "distance_m": [100, 200],
    "travel_mode": ["walk", "car"],
    "surface": ["asphalt", "gravel"],
    "one_way": [True, False]
})



export_dataframe(df=df_buildings, headers=Building_Columns, output_path="data/buildings.csv")
export_dataframe(df=df_graph, headers=graph_edges_columns, output_path="data/graph_edges.csv")
