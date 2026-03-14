import pandas as pd
import pytest

from src import data_collection
from src.data_collection import fetch_buildings_from_osm, load_buildings_csv, slugify_building_name, validate_coordinates, validate_schema


def test_slugify_building_name():
    existing = set()
    assert slugify_building_name("Engineering Auditorium", existing) == "engineering-auditorium"


def test_validate_schema_passes():
    df = pd.DataFrame(columns=["building_name", "latitude", "longitude"])
    validate_schema(df)

def test_slugify_special_chars():
    existing = set()
    assert slugify_building_name("Engineering @ Auditorium!", existing) == "engineering-auditorium"

def test_slugify_spaces():
    existing = set()
    assert slugify_building_name("Engineering   Auditorium", existing) == "engineering-auditorium"

def test_slugify_duplicates():
    existing = set()
    assert slugify_building_name("Engineering Auditorium", existing) == "engineering-auditorium"
    assert slugify_building_name("Engineering Auditorium", existing) == "engineering-auditorium-2"
    assert slugify_building_name("Engineering Auditorium", existing) == "engineering-auditorium-3"

def test_validate_coordinates_passes():
    validate_coordinates([6.67], [3.15])

def test_load_buildings_csv(tmp_path):
    csv = tmp_path / "buildings.csv"
    csv.write_text(
        """building_name,latitude,longitude
Engineering Auditorium,10,20
Engineering  Auditorium,11,21
Engineering @ Auditorium!,12,22
"""
    )
    df = load_buildings_csv(csv)
    assert list(df["building_id"]) == [
        "engineering-auditorium",
        "engineering-auditorium-2",
        "engineering-auditorium-3",
    ]

def test_slugify_empty_name_raises():
    existing = set()
    with pytest.raises(ValueError):
        slugify_building_name("!!!", existing)

def test_slugify_non_string_raises():
    existing = set()
    with pytest.raises(ValueError):
        slugify_building_name(None, existing)

def test_validate_coordinates_invalid_latitude():
    with pytest.raises(ValueError):
        validate_coordinates([100], [0])

def test_validate_coordinates_invalid_longitude():
    with pytest.raises(ValueError):
        validate_coordinates([0], [200])

def test_load_buildings_csv_missing_name_raises(tmp_path):
    csv = tmp_path / "buildings.csv"
    csv.write_text(
        """building_name,latitude,longitude
Engineering Auditorium,10,20
,11,21
"""
    )
    with pytest.raises(ValueError):
        load_buildings_csv(csv)

# non-set input must raise TypeError
def test_slugify_non_set_existing_slugs_raises():
    with pytest.raises(TypeError, match="existing_slugs must be a set"):
        slugify_building_name("Engineering Auditorium", ["engineering-auditorium"])

def test_slugify_string_existing_slugs_raises():
    with pytest.raises(TypeError, match="existing_slugs must be a set"):
        slugify_building_name("Engineering Auditorium", "engineering-auditorium")


# validate_coordinates mismatched lengths
def test_validate_coordinates_mismatched_lengths_raises():
    with pytest.raises(ValueError):
        validate_coordinates([0, 1], [0])


# load_buildings_csv with a row that slugifies to empty raises ValueError
def test_load_buildings_csv_slugifies_to_empty_raises(tmp_path):
    csv = tmp_path / "buildings.csv"
    csv.write_text(
        """building_name,latitude,longitude
Engineering Auditorium,10,20
!!!,11,21
"""
    )
    with pytest.raises(ValueError):
        load_buildings_csv(csv)


# Maintainer: dedup/collision uniqueness enforced through load_buildings_csv
def test_load_buildings_csv_dedup_exact_duplicates(tmp_path):
    """Exact duplicate names get unique suffixed IDs."""
    csv = tmp_path / "buildings.csv"
    csv.write_text(
        """building_name,latitude,longitude
Science Block,10,20
Science Block,11,21
Science Block,12,22
"""
    )
    df = load_buildings_csv(csv)
    assert list(df["building_id"]) == [
        "science-block",
        "science-block-2",
        "science-block-3",
    ]


def test_load_buildings_csv_dedup_collision_variants(tmp_path):
    """Names that are textually different but produce the same slug get unique IDs."""
    csv = tmp_path / "buildings.csv"
    csv.write_text(
        """building_name,latitude,longitude
Engineering Auditorium,10,20
Engineering  Auditorium,11,21
Engineering @ Auditorium!,12,22
"""
    )
    df = load_buildings_csv(csv)
    ids = list(df["building_id"])
    # All three must be distinct
    assert len(set(ids)) == 3
    assert ids == [
        "engineering-auditorium",
        "engineering-auditorium-2",
        "engineering-auditorium-3",
    ]


class _FakePoint:
    geom_type = "Point"

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.is_empty = False


class _FakePolygonGeom:
    geom_type = "Polygon"
    is_empty = False

    def __init__(self, x: float, y: float):
        self._point = _FakePoint(x, y)

    def representative_point(self):
        return self._point


class _FakeOsmnx:
    def __init__(self, features_df: pd.DataFrame) -> None:
        self._features_df = features_df
        self.calls = []

    def features_from_polygon(self, polygon, tags):
        self.calls.append((polygon, tags))
        return self._features_df


def test_fetch_buildings_from_osm_normalizes_named_features(monkeypatch):
    features_df = pd.DataFrame(
        {
            "name": ["Alpha Hall", None, "Beta Hall"],
            "geometry": [_FakePoint(3.15, 6.67), _FakePoint(3.16, 6.68), _FakePolygonGeom(3.17, 6.69)],
        }
    )
    fake_ox = _FakeOsmnx(features_df)
    monkeypatch.setattr(data_collection, "_import_osmnx", lambda: fake_ox)
    monkeypatch.setattr("src.graph_builder._load_boundary_polygon", lambda _path: "fake-boundary")

    result = fetch_buildings_from_osm("boundary.geojson")

    assert len(result) == 3
    assert set(result.columns) >= {"building_name", "latitude", "longitude", "building_id", "source", "source_ref"}
    assert set(result["source"]) == {"osm"}
    assert fake_ox.calls[0][1] == {"building": True}
    assert (result["building_name"].str.contains("OSM Building")).any()


def test_fetch_buildings_from_osm_handles_unnamed_features_with_fallback_name(monkeypatch):
    features_df = pd.DataFrame({"name": [None], "geometry": [_FakePoint(3.15, 6.67)]})
    monkeypatch.setattr(data_collection, "_import_osmnx", lambda: _FakeOsmnx(features_df))
    monkeypatch.setattr("src.graph_builder._load_boundary_polygon", lambda _path: "fake-boundary")

    result = fetch_buildings_from_osm("boundary.geojson")
    assert len(result) == 1
    assert result.iloc[0]["building_name"].startswith("OSM Building")
