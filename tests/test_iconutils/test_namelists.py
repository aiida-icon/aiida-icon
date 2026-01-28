import textwrap

import aiida.orm
import f90nml

from aiida_icon.iconutils import namelists


def test_namelist_to_dict_single_group():
    """Test conversion of a single namelist group."""
    nml = f90nml.reads("&run_nml\n  num_lev = 60\n  dtime = 10.0\n/")
    result = namelists.namelist_to_dict(nml)

    assert result == {"run_nml": [{"num_lev": 60, "dtime": 10.0}]}


def test_namelist_to_dict_multiple_groups():
    """Test conversion of multiple different namelist groups."""
    nml_content = textwrap.dedent("""
        &run_nml
          num_lev = 60
        /
        &grid_nml
          dynamics_grid_filename = 'grid.nc'
        /
    """)
    nml = f90nml.reads(nml_content)
    result = namelists.namelist_to_dict(nml)

    assert "run_nml" in result
    assert "grid_nml" in result
    assert result["run_nml"] == [{"num_lev": 60}]
    assert result["grid_nml"] == [{"dynamics_grid_filename": "grid.nc"}]


def test_namelist_to_dict_duplicate_groups():
    """Test conversion of duplicate namelist groups."""
    nml_content = textwrap.dedent("""
        &output_nml
          output_filename = './stream1/'
        /
        &output_nml
          output_filename = './stream2/'
        /
    """)
    nml = f90nml.reads(nml_content)
    result = namelists.namelist_to_dict(nml)

    assert len(result["output_nml"]) == 2
    assert result["output_nml"][0] == {"output_filename": "./stream1/"}
    assert result["output_nml"][1] == {"output_filename": "./stream2/"}


def test_namelist_to_dict_nested_values():
    """Test conversion with nested namelist structures."""
    nml_content = textwrap.dedent("""
        &section_nml
          param1 = 1
          param2 = 'test'
          param3 = .true.
        /
    """)
    nml = f90nml.reads(nml_content)
    result = namelists.namelist_to_dict(nml)

    assert result["section_nml"] == [{"param1": 1, "param2": "test", "param3": True}]


def test_create_namelist_singlefiledata_from_content():
    """Test creating SinglefileData from namelist string content."""
    content = "&run_nml\n  num_lev = 60\n/"

    node = namelists.create_namelist_singlefiledata_from_content(content, store=False)

    assert isinstance(node, aiida.orm.SinglefileData)
    assert node.base.attributes.get("namelist") == {"run_nml": [{"num_lev": 60}]}


def test_create_namelist_singlefiledata_from_file(tmp_path):
    """Test creating SinglefileData from namelist file."""
    nml_file = tmp_path / "test.nml"
    nml_file.write_text("&run_nml\n  num_lev = 60\n/")

    node = namelists.create_namelist_singlefiledata(nml_file, store=False)

    assert isinstance(node, aiida.orm.SinglefileData)
    assert node.base.attributes.get("namelist") == {"run_nml": [{"num_lev": 60}]}


def test_namelist_to_dict_mixed_single_and_duplicate():
    """Test conversion with mix of single and duplicate namelist groups."""
    nml_content = textwrap.dedent("""
        &run_nml
          num_lev = 60
        /
        &output_nml
          filetype = 5
        /
        &output_nml
          filetype = 2
        /
        &grid_nml
          dynamics_grid_filename = 'grid.nc'
        /
    """)
    nml = f90nml.reads(nml_content)
    result = namelists.namelist_to_dict(nml)

    # Single occurrences should still be wrapped in list
    assert result["run_nml"] == [{"num_lev": 60}]
    assert result["grid_nml"] == [{"dynamics_grid_filename": "grid.nc"}]

    # Duplicate occurrences should be in list with multiple items
    assert len(result["output_nml"]) == 2
    assert result["output_nml"][0] == {"filetype": 5}
    assert result["output_nml"][1] == {"filetype": 2}
