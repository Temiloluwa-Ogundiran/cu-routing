"""Tests for main.py CLI pipeline"""
import sys
import tempfile
from pathlib import Path
import pandas as pd
import pytest
import unittest.mock
import main

def test_validate_files_exist_with_real_files():
    """Test file validation with actual files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create real files
        buildings_file = Path(tmpdir) / "buildings.csv"
        boundary_file = Path(tmpdir) / "boundary.geojson"
        buildings_file.touch()
        boundary_file.touch()
        assert main.validate_files_exist(buildings_file, boundary_file) == True

def test_validate_files_exist_with_missing_file():
    """Test file validation when one file is missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        buildings_file = Path(tmpdir) / "buildings.csv"
        boundary_file = Path(tmpdir) / "boundary.geojson"
        buildings_file.touch()  # Only create one file
        # boundary_file not created
        assert main.validate_files_exist(buildings_file, boundary_file) == False

def test_setup_output_dir_creates_directory():
    """Test output directory creation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_dir = Path(tmpdir) / "new" / "output" / "dir"
        result = main.setup_output_dir(new_dir)
        assert result == new_dir
        assert new_dir.exists()

def test_process_buildings_adds_ids_and_saves():
    """Test buildings processing adds building_id and saves CSV"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create input CSV
        input_file = Path(tmpdir) / "input.csv"
        test_df = pd.DataFrame({
            'building_name': ['Library', 'Cafe'],
            'latitude': [6.6723, 6.6734],
            'longitude': [3.1581, 3.1592]
        })
        test_df.to_csv(input_file, index=False)
        # Process buildings
        output_dir = Path(tmpdir) / "output"
        result_df = main.process_buildings(input_file, output_dir)
        # Check result
        assert 'building_id' in result_df.columns
        assert result_df['building_id'].iloc[0] == 'library'
        assert result_df['building_id'].iloc[1] == 'cafe'
        # Check file was saved
        assert (output_dir / "buildings.csv").exists()


def test_build_graph_creates_edges_csv():
    """Test graph building creates edges CSV (even if empty)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a MINIMAL valid GeoJSON polygon
        boundary_file = Path(tmpdir) / "boundary.geojson"

        # This is a tiny valid GeoJSON (a square around 0,0)
        valid_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0], [1, 0], [1, 1], [0, 1], [0, 0]
                ]]
            }
        }

        import json
        with open(boundary_file, 'w') as f:
            json.dump(valid_geojson, f)

        # Build graph
        output_dir = Path(tmpdir) / "output"
        graph = main.build_graph(boundary_file, output_dir)

        # Check edges file was created
        assert (output_dir / "graph_edges.csv").exists()

def test_calculate_routes_creates_routes_csv():
    """Test route calculation creates routes CSV (even if empty)"""
    # Create minimal test data
    buildings_df = pd.DataFrame({
        'building_id': ['lib', 'cafe'],
        'building_name': ['Library', 'Cafe'],
        'latitude': [6.6723, 6.6734],
        'longitude': [3.1581, 3.1592]
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        # Use None as graph (will trigger NotImplementedError path)
        result_df = main.calculate_routes(None, buildings_df, output_dir)
        # Check routes file was created
        assert (output_dir / "routes.csv").exists()

def test_main_runs_without_crashing():
    """Test that main function runs without crashing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy input files
        buildings_file = Path(tmpdir) / "buildings.csv"
        boundary_file = Path(tmpdir) / "boundary.geojson"
        # Create buildings CSV
        pd.DataFrame({
            'building_name': ['Library'],
            'latitude': [6.6723],
            'longitude': [3.1581]
        }).to_csv(buildings_file, index=False)
        boundary_file.touch()
        output_dir = Path(tmpdir) / "output"
        # Mock command line arguments
        import sys
        sys.argv = [
            "main.py",
            "--input", str(buildings_file),
            "--boundary", str(boundary_file),
            "--output", str(output_dir)
        ]
        # Run main
        result = main.main()
        # Should return 0 (success)
        assert result == 0
        # Check all output files created
        assert (output_dir / "buildings.csv").exists()
        assert (output_dir / "graph_edges.csv").exists()
        assert (output_dir / "routes.csv").exists()

# NEW TEST 1: routes.csv has expected columns when 0 buildings
def test_routes_csv_columns_with_zero_buildings():
    """Test that routes.csv has correct columns even with no buildings"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty buildings file (only headers)
        buildings_file = Path(tmpdir) / "buildings.csv"
        pd.DataFrame(columns=['building_name', 'latitude', 'longitude']).to_csv(buildings_file, index=False)
        boundary_file = Path(tmpdir) / "boundary.geojson"
        boundary_file.touch()
        output_dir = Path(tmpdir) / "output"
        # Run main
        sys.argv = ["main.py", "--input", str(buildings_file),
                    "--boundary", str(boundary_file), "--output", str(output_dir)]
        main.main()
        # Check routes.csv exists and has correct columns
        routes_file = output_dir / "routes.csv"
        assert routes_file.exists()
        routes_df = pd.read_csv(routes_file)
        expected_columns = [
            'origin_building_id', 'destination_building_id', 'algorithm',
            'distance_m', 'estimated_time_min', 'path_node_count',
            'path_nodes', 'path_buildings', 'computed_at'
        ]
        for col in expected_columns:
            assert col in routes_df.columns, f"Missing column: {col}"

# NEW TEST 2: routes.csv has expected columns when 1 building
def test_routes_csv_columns_with_one_building():
    """Test that routes.csv has correct columns with only one building"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create buildings file with 1 building
        buildings_file = Path(tmpdir) / "buildings.csv"
        pd.DataFrame({
            'building_name': ['Library'],
            'latitude': [6.6723],
            'longitude': [3.1581]
        }).to_csv(buildings_file, index=False)
        boundary_file = Path(tmpdir) / "boundary.geojson"
        boundary_file.touch()
        output_dir = Path(tmpdir) / "output"
        # Run main
        sys.argv = ["main.py", "--input", str(buildings_file),
                    "--boundary", str(boundary_file), "--output", str(output_dir)]
        main.main()
        # Check routes.csv exists and has correct columns
        routes_file = output_dir / "routes.csv"
        assert routes_file.exists()
        routes_df = pd.read_csv(routes_file)
        expected_columns = [
            'origin_building_id', 'destination_building_id', 'algorithm',
            'distance_m', 'estimated_time_min', 'path_node_count',
            'path_nodes', 'path_buildings', 'computed_at'
        ]
        for col in expected_columns:
            assert col in routes_df.columns, f"Missing column: {col}"
        # Should have 0 routes (since only 1 building)
        assert len(routes_df) == 0

# NEW TEST 3: graph_edges.csv has expected columns when graph has zero edges
def test_graph_edges_csv_columns_with_empty_graph():
    """Test that graph_edges.csv has correct columns even when graph is empty"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal input
        buildings_file = Path(tmpdir) / "buildings.csv"
        pd.DataFrame({
            'building_name': ['Library'],
            'latitude': [6.6723],
            'longitude': [3.1581]
        }).to_csv(buildings_file, index=False)
        boundary_file = Path(tmpdir) / "boundary.geojson"
        boundary_file.touch()
        output_dir = Path(tmpdir) / "output"
        # Run main
        sys.argv = ["main.py", "--input", str(buildings_file),
                    "--boundary", str(boundary_file), "--output", str(output_dir)]
        main.main()
        # Check graph_edges.csv exists and has correct columns
        edges_file = output_dir / "graph_edges.csv"
        assert edges_file.exists()
        edges_df = pd.read_csv(edges_file)
        expected_columns = ["from_node", "to_node", "distance_m"]
        for col in expected_columns:
            assert col in edges_df.columns, f"Missing column: {col}"

# NEW TEST 4: validate_files_exist returns False for directories
def test_validate_files_exist_with_directories():
    """Test that validate_files_exist returns False when given directories instead of files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directories (not files)
        buildings_dir = Path(tmpdir) / "buildings_dir"
        boundary_dir = Path(tmpdir) / "boundary_dir"
        buildings_dir.mkdir()
        boundary_dir.mkdir()
        # Validation should fail (these are directories, not files)
        assert main.validate_files_exist(buildings_dir, boundary_dir) == False
        # Create real files
        buildings_file = Path(tmpdir) / "buildings.csv"
        boundary_file = Path(tmpdir) / "boundary.geojson"
        buildings_file.touch()
        boundary_file.touch()
        # Validation should pass
        assert main.validate_files_exist(buildings_file, boundary_file) == True
        # Mix one file, one directory should fail
        assert main.validate_files_exist(buildings_file, boundary_dir) == False
        assert main.validate_files_exist(buildings_dir, boundary_file) == False


def test_build_graph_handles_exception():
    """Test build_graph gracefully handles graph builder failures"""
    with tempfile.TemporaryDirectory() as tmpdir:
        boundary_file = Path(tmpdir) / "boundary.geojson"
        boundary_file.touch()
        output_dir = Path(tmpdir) / "output"
        # Mock the graph builder to raise an exception
        with unittest.mock.patch('src.graph_builder.build_walking_graph_from_polygon') as mock_builder:
            mock_builder.side_effect = Exception("OSM connection failed")
            # This should NOT crash
            graph = main.build_graph(boundary_file, output_dir)
            # Should return None
            assert graph is None
            # Should still create empty CSV with headers
            edges_file = output_dir / "graph_edges.csv"
            assert edges_file.exists()
            edges_df = pd.read_csv(edges_file)
            assert list(edges_df.columns) == ["from_node", "to_node", "distance_m"]
            assert len(edges_df) == 0


def test_process_buildings_missing_columns():
    """Test process_buildings raises error when required columns missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create CSV missing required columns
        bad_file = Path(tmpdir) / "bad.csv"
        pd.DataFrame({
            'wrong_name': ['Library'],
            'lat': [6.6723],
            'lon': [3.1581]
        }).to_csv(bad_file, index=False)
        output_dir = Path(tmpdir) / "output"
        # Should raise error about missing columns
        with pytest.raises(ValueError, match="Missing required columns"):
            main.process_buildings(bad_file, output_dir)


def test_calculate_routes_not_implemented():
    """Test calculate_routes handles NotImplementedError gracefully"""
    buildings_df = pd.DataFrame({
        'building_id': ['lib', 'cafe'],
        'building_name': ['Library', 'Cafe'],
        'latitude': [6.6723, 6.6734],
        'longitude': [3.1581, 3.1592]
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        # Mock the router to raise NotImplementedError
        with unittest.mock.patch('src.router.map_building_to_nearest_node') as mock_map:
            mock_map.side_effect = NotImplementedError("Not implemented")
            result_df = main.calculate_routes(None, buildings_df, output_dir)
            # Should return empty DataFrame with correct schema
            expected_columns = [
                'origin_building_id', 'destination_building_id', 'algorithm',
                'distance_m', 'estimated_time_min', 'path_node_count',
                'path_nodes', 'path_buildings', 'computed_at'
            ]
            for col in expected_columns:
                assert col in result_df.columns
            assert len(result_df) == 0
            # Should still create CSV
            routes_file = output_dir / "routes.csv"
            assert routes_file.exists()


def test_main_returns_1_on_validation_failure():
    """Test main returns 1 (error) when file validation fails"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create only one file (other missing)
        buildings_file = Path(tmpdir) / "buildings.csv"
        buildings_file.touch()
        # boundary_file not created
        output_dir = Path(tmpdir) / "output"
        # Mock args to point to non-existent boundary file
        import sys
        sys.argv = [
            "main.py",
            "--input", str(buildings_file),
            "--boundary", str(Path(tmpdir) / "missing.geojson"),
            "--output", str(output_dir)
        ]
        # Main should return 1 (error)
        result = main.main()
        assert result == 1
        # No output files should be created
        assert not (output_dir / "buildings.csv").exists()
        assert not (output_dir / "graph_edges.csv").exists()
        assert not (output_dir / "routes.csv").exists()
