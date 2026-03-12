"""Tests for main.py CLI pipeline"""
import tempfile
from pathlib import Path
import pandas as pd
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
        # Create dummy boundary file
        boundary_file = Path(tmpdir) / "boundary.geojson"
        boundary_file.touch()
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
