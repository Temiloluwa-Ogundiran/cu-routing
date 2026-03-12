"""Building coordinate ingestion and validation."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = ("building_name", "latitude", "longitude")


def validate_schema(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
 
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
 
    return df
