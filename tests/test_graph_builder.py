from __future__ import annotations

import builtins
import json

import networkx as nx
import pytest

from src import graph_builder


def _write_boundary(path) -> None:
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [3.146, 6.669],
                            [3.161, 6.669],
                            [3.161, 6.678],
                            [3.146, 6.678],
                            [3.146, 6.669],
                        ]
                    ],
                },
                "properties": {},
            }
        ],
    }
    path.write_text(json.dumps(feature_collection), encoding="utf-8")


class _FakePolygon:
    geom_type = "Polygon"
    is_empty = False


class _FakeMultiPolygon:
    geom_type = "MultiPolygon"
    is_empty = False
    geoms = ()


class _FakeInvalidPolygon(_FakePolygon):
    is_valid = False
    area = 1.0


class _FakeZeroAreaPolygon(_FakePolygon):
    is_valid = True
    area = 0.0


def _patch_shapely(monkeypatch, *, shape_fn=None) -> None:
    if shape_fn is None:
        shape_fn = lambda _: _FakePolygon()
    monkeypatch.setattr(
        graph_builder,
        "_import_shapely_geometry",
        lambda: (_FakeMultiPolygon, _FakePolygon, shape_fn),
    )


class _FakeDistanceModule:
    def __init__(self, length_to_fill: float = 42.0) -> None:
        self.length_to_fill = length_to_fill
        self.called = False

    def add_edge_lengths(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        self.called = True
        for _, _, _, edge_data in graph.edges(keys=True, data=True):
            edge_data.setdefault("length", self.length_to_fill)
        return graph


class _FakeDistanceModuleInPlaceNoneReturn:
    def __init__(self, length_to_fill: float = 11.0) -> None:
        self.length_to_fill = length_to_fill
        self.called = False

    def add_edge_lengths(self, graph: nx.MultiDiGraph) -> None:
        self.called = True
        for _, _, _, edge_data in graph.edges(keys=True, data=True):
            edge_data.setdefault("length", self.length_to_fill)
        return None


class _FakeDistanceModuleWithEdgesParameter:
    def __init__(self, length_to_fill: float = 17.0) -> None:
        self.length_to_fill = length_to_fill
        self.received_edges = None

    def add_edge_lengths(self, graph: nx.MultiDiGraph, edges=None) -> nx.MultiDiGraph:
        self.received_edges = edges
        edges_to_fill = edges if edges is not None else list(graph.edges(keys=True))
        for source, target, key in edges_to_fill:
            graph.edges[source, target, key]["length"] = self.length_to_fill
        return graph


class _FakeDistanceModuleOverwriteAll:
    def __init__(self, length_to_fill: float = 99.0) -> None:
        self.length_to_fill = length_to_fill
        self.called = False

    def add_edge_lengths(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        self.called = True
        for _, _, _, edge_data in graph.edges(keys=True, data=True):
            edge_data["length"] = self.length_to_fill
        return graph


class _FakeDistanceModuleEdgesTypeError:
    def __init__(self, length_to_fill: float = 33.0) -> None:
        self.length_to_fill = length_to_fill
        self.called_with_edges = False
        self.called_without_edges = False

    def add_edge_lengths(self, graph: nx.MultiDiGraph, edges=None) -> nx.MultiDiGraph:
        if edges is not None:
            self.called_with_edges = True
            raise TypeError("edges kw not accepted at runtime")
        self.called_without_edges = True
        for _, _, _, edge_data in graph.edges(keys=True, data=True):
            edge_data["length"] = self.length_to_fill
        return graph


class _FakeDistanceModuleEdgesParameterOverwriteAll:
    def __init__(self, length_to_fill: float = 55.0) -> None:
        self.length_to_fill = length_to_fill
        self.received_edges = None

    def add_edge_lengths(self, graph: nx.MultiDiGraph, edges=None) -> nx.MultiDiGraph:
        self.received_edges = edges
        for _, _, _, edge_data in graph.edges(keys=True, data=True):
            edge_data["length"] = self.length_to_fill
        return graph


class _FakeDistanceModuleReturnsNewGraph:
    def __init__(self, length_to_fill: float = 66.0) -> None:
        self.length_to_fill = length_to_fill
        self.called = False
        self.returned_graph = None

    def add_edge_lengths(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        self.called = True
        new_graph = nx.MultiDiGraph(graph)
        for _, _, _, edge_data in new_graph.edges(keys=True, data=True):
            edge_data["length"] = self.length_to_fill
        self.returned_graph = new_graph
        return new_graph


class _FakeOsmnx:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.distance = _FakeDistanceModule()
        self.received_polygon = None
        self.received_kwargs = {}

    def graph_from_polygon(self, polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        self.received_polygon = polygon
        self.received_kwargs = {"network_type": network_type, "simplify": simplify}
        return self._graph


class _FakeOsmnxInPlaceAddEdgeLengths:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.distance = _FakeDistanceModuleInPlaceNoneReturn()

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return self._graph


class _FakeOsmnxEdgesArgument:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.distance = _FakeDistanceModuleWithEdgesParameter()

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return self._graph


class _FakeOsmnxOverwriteAllLengths:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.distance = _FakeDistanceModuleOverwriteAll()

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return self._graph


class _FakeOsmnxEdgesKwTypeError:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.distance = _FakeDistanceModuleEdgesTypeError()

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return self._graph


class _FakeOsmnxEdgesParameterOverwriteAll:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.distance = _FakeDistanceModuleEdgesParameterOverwriteAll()

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return self._graph


class _FakeOsmnxReturnsNewGraph:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.distance = _FakeDistanceModuleReturnsNewGraph()

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return self._graph


class _FakeOsmnxTopLevelAddEdgeLengths:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph
        self.received_kwargs = {}
        self.top_level_called = False

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        self.received_kwargs = {"network_type": network_type, "simplify": simplify}
        return self._graph

    def add_edge_lengths(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        self.top_level_called = True
        for _, _, _, edge_data in graph.edges(keys=True, data=True):
            edge_data.setdefault("length", 21.0)
        return graph


class _FakeOsmnxWithoutAddEdgeLengths:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self._graph = graph

    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return self._graph


class _FakeOsmnxEmptyGraph:
    def graph_from_polygon(self, _polygon, *, network_type: str, simplify: bool) -> nx.MultiDiGraph:
        return nx.MultiDiGraph()


class _FakeOsmnxNoAddLengthAPIs:
    distance = object()


def test_build_walking_graph_loads_walk_network_and_sets_distance_m(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=15.5)
    fake_osmnx = _FakeOsmnx(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert isinstance(result, nx.MultiDiGraph)
    assert fake_osmnx.received_kwargs == {"network_type": "walk", "simplify": True}
    assert fake_osmnx.received_polygon.geom_type == "Polygon"
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(15.5)
    assert fake_osmnx.distance.called is False


def test_build_walking_graph_accepts_path_object(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=10.0)
    fake_osmnx = _FakeOsmnx(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(boundary_path)

    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(10.0)


def test_build_walking_graph_adds_missing_length_before_distance_m(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0)
    fake_osmnx = _FakeOsmnx(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.distance.called is True
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(42.0)


def test_build_walking_graph_supports_in_place_add_edge_lengths_returning_none(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0)
    fake_osmnx = _FakeOsmnxInPlaceAddEdgeLengths(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.distance.called is True
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(11.0)


def test_build_walking_graph_passes_missing_edges_when_supported(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=8.5)
    graph.add_edge(2, 3, key=0)
    fake_osmnx = _FakeOsmnxEdgesArgument(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.distance.received_edges == [(2, 3, 0)]
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(8.5)
    assert result.edges[2, 3, 0]["distance_m"] == pytest.approx(17.0)


def test_build_walking_graph_preserves_existing_lengths_if_fallback_overwrites_all(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=15.5)
    graph.add_edge(2, 3, key=0)
    fake_osmnx = _FakeOsmnxOverwriteAllLengths(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.distance.called is True
    assert result.edges[1, 2, 0]["length"] == pytest.approx(15.5)
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(15.5)
    assert result.edges[2, 3, 0]["distance_m"] == pytest.approx(99.0)


def test_build_walking_graph_falls_back_when_edges_kw_raises_type_error(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=12.0)
    graph.add_edge(2, 3, key=0)
    fake_osmnx = _FakeOsmnxEdgesKwTypeError(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.distance.called_with_edges is True
    assert fake_osmnx.distance.called_without_edges is True
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(12.0)
    assert result.edges[2, 3, 0]["distance_m"] == pytest.approx(33.0)


def test_build_walking_graph_restores_preserved_lengths_when_edges_kw_overwrites_all(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=14.0)
    graph.add_edge(2, 3, key=0)
    fake_osmnx = _FakeOsmnxEdgesParameterOverwriteAll(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.distance.received_edges == [(2, 3, 0)]
    assert result.edges[1, 2, 0]["length"] == pytest.approx(14.0)
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(14.0)
    assert result.edges[2, 3, 0]["distance_m"] == pytest.approx(55.0)


def test_build_walking_graph_uses_graph_returned_by_add_edge_lengths(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=7.5)
    graph.add_edge(2, 3, key=0)
    fake_osmnx = _FakeOsmnxReturnsNewGraph(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.distance.called is True
    assert result is fake_osmnx.distance.returned_graph
    assert result.edges[1, 2, 0]["length"] == pytest.approx(7.5)
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(7.5)
    assert result.edges[2, 3, 0]["distance_m"] == pytest.approx(66.0)


def test_build_walking_graph_uses_top_level_add_edge_lengths_fallback(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0)
    fake_osmnx = _FakeOsmnxTopLevelAddEdgeLengths(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    result = graph_builder.build_walking_graph_from_polygon(str(boundary_path))

    assert fake_osmnx.top_level_called is True
    assert result.edges[1, 2, 0]["distance_m"] == pytest.approx(21.0)


def test_build_walking_graph_raises_when_add_edge_lengths_unavailable(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0)
    fake_osmnx = _FakeOsmnxWithoutAddEdgeLengths(graph)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: fake_osmnx)

    with pytest.raises(RuntimeError, match="does not expose add_edge_lengths"):
        graph_builder.build_walking_graph_from_polygon(str(boundary_path))


def test_build_walking_graph_raises_for_empty_osmnx_graph(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    monkeypatch.setattr(graph_builder, "_import_osmnx", lambda: _FakeOsmnxEmptyGraph())

    with pytest.raises(ValueError, match="empty walking graph"):
        graph_builder.build_walking_graph_from_polygon(str(boundary_path))


def test_build_walking_graph_rejects_invalid_geojson(tmp_path):
    invalid_boundary_path = tmp_path / "campus_boundary.geojson"
    invalid_boundary_path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="No polygon geometry"):
        graph_builder.build_walking_graph_from_polygon(str(invalid_boundary_path))


def test_load_boundary_polygon_rejects_invalid_json(tmp_path):
    invalid_boundary_path = tmp_path / "campus_boundary.geojson"
    invalid_boundary_path.write_text("this is not json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid boundary GeoJSON"):
        graph_builder._load_boundary_polygon(str(invalid_boundary_path))


def test_load_boundary_polygon_rejects_missing_file(tmp_path):
    missing_boundary_path = tmp_path / "missing_boundary.geojson"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        graph_builder._load_boundary_polygon(str(missing_boundary_path))


def test_load_boundary_polygon_rejects_directory_path(tmp_path):
    boundary_dir = tmp_path / "boundary_dir"
    boundary_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="not a file"):
        graph_builder._load_boundary_polygon(str(boundary_dir))


def test_load_boundary_polygon_rejects_malformed_geometry_mapping(tmp_path):
    invalid_geometry_path = tmp_path / "campus_boundary.geojson"
    invalid_geometry_path.write_text(
        json.dumps({"type": "Feature", "geometry": {"coordinates": []}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(invalid_geometry_path))


def test_load_boundary_polygon_rejects_empty_coordinates(tmp_path):
    invalid_geometry_path = tmp_path / "campus_boundary.geojson"
    invalid_geometry_path.write_text(
        json.dumps({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(invalid_geometry_path))


def test_load_boundary_polygon_rejects_polygon_with_invalid_outer_ring_even_if_inner_valid(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[3.146, 6.669], [3.161, 6.669], [3.146, 6.669]],
                [[3.148, 6.671], [3.149, 6.671], [3.149, 6.672], [3.148, 6.672], [3.148, 6.671]],
            ],
        },
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    _patch_shapely(monkeypatch)
    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_rejects_unclosed_polygon_ring(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[3.146, 6.669], [3.161, 6.669], [3.161, 6.678], [3.146, 6.678]]],
        },
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    _patch_shapely(monkeypatch)
    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_rejects_unclosed_multipolygon_outer_ring(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[3.14, 6.66], [3.145, 6.66], [3.145, 6.665], [3.14, 6.665]]],
            [[[3.15, 6.67], [3.16, 6.67], [3.16, 6.68], [3.15, 6.68], [3.15, 6.67]]],
        ],
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    _patch_shapely(monkeypatch)
    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_searches_feature_collection_beyond_first(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [3.15, 6.67]}},
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[3.146, 6.669], [3.161, 6.669], [3.161, 6.678], [3.146, 6.678], [3.146, 6.669]]],
                },
            },
        ],
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    seen = {}

    def _shape_fn(geometry):
        seen["geometry"] = geometry
        return _FakePolygon()

    _patch_shapely(monkeypatch, shape_fn=_shape_fn)
    polygon = graph_builder._load_boundary_polygon(str(boundary_path))

    assert isinstance(polygon, _FakePolygon)
    assert seen["geometry"]["type"] == "Polygon"


def test_load_boundary_polygon_preserves_all_polygon_features_in_feature_collection(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[3.14, 6.66], [3.145, 6.66], [3.145, 6.665], [3.14, 6.665], [3.14, 6.66]]],
                },
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[3.15, 6.67], [3.16, 6.67], [3.16, 6.68], [3.15, 6.68], [3.15, 6.67]]],
                },
            },
        ],
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    seen = {}

    def _shape_fn(geometry):
        seen["geometry"] = geometry
        return _FakeMultiPolygon()

    _patch_shapely(monkeypatch, shape_fn=_shape_fn)
    geometry = graph_builder._load_boundary_polygon(str(boundary_path))

    assert isinstance(geometry, _FakeMultiPolygon)
    assert seen["geometry"]["type"] == "MultiPolygon"
    assert len(seen["geometry"]["coordinates"]) == 2


def test_load_boundary_polygon_supports_geometry_collection(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Point", "coordinates": [3.15, 6.67]},
                {
                    "type": "Polygon",
                    "coordinates": [[[3.146, 6.669], [3.161, 6.669], [3.161, 6.678], [3.146, 6.678], [3.146, 6.669]]],
                },
            ],
        },
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    seen = {}

    def _shape_fn(geometry):
        seen["geometry"] = geometry
        return _FakePolygon()

    _patch_shapely(monkeypatch, shape_fn=_shape_fn)
    polygon = graph_builder._load_boundary_polygon(str(boundary_path))

    assert isinstance(polygon, _FakePolygon)
    assert seen["geometry"]["type"] == "Polygon"


def test_load_boundary_polygon_preserves_multipolygon(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[3.14, 6.66], [3.145, 6.66], [3.145, 6.665], [3.14, 6.665], [3.14, 6.66]]],
            [[[3.15, 6.67], [3.16, 6.67], [3.16, 6.68], [3.15, 6.68], [3.15, 6.67]]],
        ],
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    _patch_shapely(monkeypatch, shape_fn=lambda _: _FakeMultiPolygon())
    geometry = graph_builder._load_boundary_polygon(str(boundary_path))

    assert isinstance(geometry, _FakeMultiPolygon)


def test_is_polygon_geometry_mapping_accepts_tuple_coordinates():
    geometry = {
        "type": "Polygon",
        "coordinates": (((3.146, 6.669), (3.161, 6.669), (3.161, 6.678), (3.146, 6.678), (3.146, 6.669)),),
    }

    assert graph_builder._is_polygon_geometry_mapping(geometry) is True


def test_resolve_add_edge_lengths_error_lists_checked_apis():
    with pytest.raises(RuntimeError, match=r"distance\.add_edge_lengths=False"):
        graph_builder._resolve_add_edge_lengths(_FakeOsmnxNoAddLengthAPIs())


def test_import_osmnx_wraps_import_error(monkeypatch):
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "osmnx":
            raise ImportError("missing osmnx")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with pytest.raises(RuntimeError, match="osmnx is required"):
        graph_builder._import_osmnx()


def test_import_shapely_wraps_import_error(monkeypatch):
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name.startswith("shapely"):
            raise ImportError("missing shapely")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with pytest.raises(RuntimeError, match="shapely is required"):
        graph_builder._import_shapely_geometry()


def test_load_boundary_polygon_wraps_shape_exceptions(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    class _CustomShapeError(Exception):
        pass

    def _raise_shape(_geometry):
        raise _CustomShapeError("bad geometry internals")

    _patch_shapely(monkeypatch, shape_fn=_raise_shape)
    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_rejects_empty_shapely_geometry(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    class _EmptyPolygon(_FakePolygon):
        is_empty = True

    _patch_shapely(monkeypatch, shape_fn=lambda _geometry: _EmptyPolygon())
    with pytest.raises(ValueError, match="Boundary geometry is empty"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_rejects_invalid_shapely_geometry(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch, shape_fn=lambda _geometry: _FakeInvalidPolygon())
    with pytest.raises(ValueError, match="invalid or has zero area"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_rejects_zero_area_shapely_geometry(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch, shape_fn=lambda _geometry: _FakeZeroAreaPolygon())
    with pytest.raises(ValueError, match="invalid or has zero area"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_rejects_non_numeric_coordinates(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[["3.146", 6.669], [3.161, 6.669], [3.161, 6.678], [3.146, 6.678], ["3.146", 6.669]]],
        },
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    _patch_shapely(monkeypatch)
    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_rejects_boolean_coordinates(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[True, 6.669], [3.161, 6.669], [3.161, 6.678], [3.146, 6.678], [True, 6.669]]],
        },
    }
    boundary_path.write_text(json.dumps(payload), encoding="utf-8")

    _patch_shapely(monkeypatch)
    with pytest.raises(ValueError, match="Boundary geometry is not a valid GeoJSON geometry"):
        graph_builder._load_boundary_polygon(str(boundary_path))


def test_load_boundary_polygon_accepts_path_object(tmp_path, monkeypatch):
    boundary_path = tmp_path / "campus_boundary.geojson"
    _write_boundary(boundary_path)

    _patch_shapely(monkeypatch)
    polygon = graph_builder._load_boundary_polygon(boundary_path)

    assert isinstance(polygon, _FakePolygon)


def test_normalise_edge_distances_rejects_non_numeric_length():
    graph = nx.MultiDiGraph()
    graph.add_edge(10, 20, key=0, length="unknown")

    with pytest.raises(ValueError, match=r"Edge length is not numeric.*10->20.*key=0"):
        graph_builder._normalise_edge_distances(graph)


def test_normalise_edge_distances_rejects_non_positive_length():
    graph = nx.MultiDiGraph()
    graph.add_edge(10, 20, key=1, length=0)

    with pytest.raises(ValueError, match=r"Edge length must be positive.*10->20.*key=1"):
        graph_builder._normalise_edge_distances(graph)


def test_normalise_edge_distances_rejects_boolean_length():
    graph = nx.MultiDiGraph()
    graph.add_edge(10, 20, key=5, length=True)

    with pytest.raises(ValueError, match=r"not boolean.*10->20.*key=5"):
        graph_builder._normalise_edge_distances(graph)


def test_normalise_edge_distances_rejects_non_finite_length():
    graph = nx.MultiDiGraph()
    graph.add_edge(10, 20, key=2, length=float("nan"))

    with pytest.raises(ValueError, match=r"must be finite.*10->20.*key=2"):
        graph_builder._normalise_edge_distances(graph)


def test_normalise_edge_distances_rejects_positive_infinity_length():
    graph = nx.MultiDiGraph()
    graph.add_edge(10, 20, key=3, length=float("inf"))

    with pytest.raises(ValueError, match=r"must be finite.*10->20.*key=3"):
        graph_builder._normalise_edge_distances(graph)


def test_normalise_edge_distances_rejects_negative_infinity_length():
    graph = nx.MultiDiGraph()
    graph.add_edge(10, 20, key=4, length=float("-inf"))

    with pytest.raises(ValueError, match=r"must be finite.*10->20.*key=4"):
        graph_builder._normalise_edge_distances(graph)
