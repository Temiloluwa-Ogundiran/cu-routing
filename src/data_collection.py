"""Building coordinate ingestion and validation."""

from __future__ import annotations

import re
from os import PathLike
from typing import Any, Iterable

import pandas as pd


REQUIRED_COLUMNS = ("building_name", "latitude", "longitude")


def validate_schema(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _import_osmnx() -> Any:
    try:
        import osmnx as ox
    except ImportError as exc:  # pragma: no cover - depends on environment setup
        raise RuntimeError("osmnx is required to fetch building data from OpenStreetMap.") from exc
    return ox


def slugify_building_name(name: str, existing_slugs=None) -> str:
    if not isinstance(name, str) or name == "":
        raise ValueError("building_name must be a non-empty string")

    # Convert to lowercase, remove special characters
    slug = re.sub(r"[^a-z0-9\s-]", "", name.lower().strip())
    # replace spaces with hyphens.
    slug = re.sub(r"\s+", "-", slug)
    # replace multiple hyphens with a single one.
    slug = re.sub(r"-+", "-", slug).strip("-")

    if not slug:
        raise ValueError("Empty building_name after slugification is not allowed")

    # Handles Duplicate
    if existing_slugs is None:
        return slug

    if not isinstance(existing_slugs, set):
        raise TypeError("existing_slugs must be a set")

    # Deduplication logic
    unique_slug = slug
    counter = 2
    while unique_slug in existing_slugs:
        unique_slug = f"{slug}-{counter}"
        counter += 1
 
    existing_slugs.add(unique_slug)
    return unique_slug


def validate_coordinates(latitudes: Iterable[float], longitudes: Iterable[float]) -> None:
    lats, lons = list(latitudes), list(longitudes)
    if len(lats) != len(lons):
        raise ValueError(f"Mismatched coordinate lengths: {len(lats)} lats, {len(lons)} lons")

    for index, (lat, lon) in enumerate(zip(lats, lons)):
        if not (-90 <= float(lat) <= 90):
            raise ValueError(f"Invalid latitude at row {index}: {lat}")
        if not (-180 <= float(lon) <= 180):
            raise ValueError(f"Invalid longitude at row {index}: {lon}")


def _geometry_to_point(geometry: Any) -> Any:
    if geometry is None or getattr(geometry, "is_empty", False):
        return None

    geom_type = getattr(geometry, "geom_type", "")
    if geom_type == "Point":
        return geometry

    if hasattr(geometry, "representative_point"):
        try:
            return geometry.representative_point()
        except Exception:
            return None
    return None


def _normalise_osm_buildings(features_df: pd.DataFrame) -> pd.DataFrame:
    if "geometry" not in features_df.columns:
        raise ValueError("OSM building features are missing required column: geometry.")

    working_df = features_df.reset_index()
    if "element" not in working_df.columns:
        working_df["element"] = "feature"
    if "id" not in working_df.columns:
        working_df["id"] = working_df.index.astype(str)

    existing_slugs: set[str] = set()
    records: list[dict[str, Any]] = []
    for row in working_df.itertuples(index=False):
        element = str(getattr(row, "element", "unknown"))
        osm_id = str(getattr(row, "id", "unknown"))

        point = _geometry_to_point(getattr(row, "geometry", None))
        if point is None:
            continue

        try:
            latitude = float(point.y)
            longitude = float(point.x)
        except (TypeError, ValueError, AttributeError):
            continue

        raw_name = getattr(row, "name", None)
        if isinstance(raw_name, str) and raw_name.strip():
            building_name = raw_name.strip()
        else:
            building_type = getattr(row, "building", None)
            if isinstance(building_type, str) and building_type.strip() and building_type.strip().lower() != "yes":
                label = building_type.strip().replace("_", " ")
                building_name = f"OSM {label.title()} {element} {osm_id}"
            else:
                building_name = f"OSM Building {element} {osm_id}"

        records.append(
            {
                "building_name": building_name,
                "latitude": latitude,
                "longitude": longitude,
                "building_id": slugify_building_name(building_name, existing_slugs),
                "source": "osm",
                "source_ref": f"{element}/{osm_id}",
            }
        )

    buildings_df = pd.DataFrame(records)
    if buildings_df.empty:
        return pd.DataFrame(columns=["building_name", "latitude", "longitude", "building_id", "source", "source_ref"])

    validate_coordinates(buildings_df["latitude"], buildings_df["longitude"])
    return buildings_df


def fetch_buildings_from_osm(polygon_geojson_path: str | PathLike) -> pd.DataFrame:
    from src.graph_builder import _load_boundary_polygon

    polygon = _load_boundary_polygon(str(polygon_geojson_path))
    ox = _import_osmnx()

    try:
        features = ox.features_from_polygon(polygon, tags={"building": True})
    except Exception as exc:
        raise RuntimeError("Failed to fetch building features from OpenStreetMap.") from exc

    if features is None or features.empty:
        raise ValueError("OpenStreetMap returned no building features for the provided boundary.")

    buildings_df = _normalise_osm_buildings(features)
    if buildings_df.empty:
        raise ValueError("No building features with valid geometry were found in OpenStreetMap response.")
    return buildings_df


def load_buildings_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    validate_schema(df)
    if df["building_name"].isna().any():
        row = df["building_name"].isna().idxmax()
        raise ValueError(f"building_name missing at row {row}")

    validate_coordinates(df["latitude"], df["longitude"])

    existing_slugs = set()

    df["building_id"] = [
        slugify_building_name(name, existing_slugs)
        for name in df["building_name"]
    ]

    df["source"] = "csv"
    return df
