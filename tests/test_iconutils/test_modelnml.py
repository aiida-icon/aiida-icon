import pathlib

import f90nml

from aiida_icon.iconutils import modelnml


class TestReadOutputStreamInfos:
    """Test the parsing of output stream information from model namelists."""

    def test_missing_output_nml_section(self):
        """Test handling when output_nml section is completely missing."""
        namelist_data = f90nml.Namelist({'grid_nml': {'dynamics_grid_filename': 'test.nc'}})
        result = modelnml.read_output_stream_infos(namelist_data)
        assert result == []

    def test_empty_output_nml_section(self):
        """Test handling when output_nml section exists but is empty."""
        namelist_data = f90nml.Namelist({'output_nml': {}})
        result = modelnml.read_output_stream_infos(namelist_data)
        
        assert len(result) == 1
        assert result[0].output_filename == ""
        assert result[0].path == pathlib.Path(".")
        assert result[0].stream_index == 0

    def test_missing_output_filename(self):
        """Test handling when output_filename is not specified."""
        namelist_data = f90nml.Namelist({'output_nml': {'filetype': 5}})
        result = modelnml.read_output_stream_infos(namelist_data)
        
        assert len(result) == 1
        assert result[0].output_filename == ""
        assert result[0].path == pathlib.Path(".")

    def test_with_output_filename(self):
        """Test normal case with output_filename."""
        namelist_data = f90nml.Namelist({
            'output_nml': {'output_filename': './test_output/', 'filetype': 5}
        })
        result = modelnml.read_output_stream_infos(namelist_data)
        
        assert len(result) == 1
        assert result[0].output_filename == "./test_output/"
        assert result[0].path == pathlib.Path("./test_output")

    def test_multiple_output_streams(self):
        """Test parsing multiple output streams."""
        namelist_data = f90nml.Namelist({
            'output_nml': [
                {'output_filename': './stream1/', 'filetype': 5},
                {'output_filename': './stream2/', 'filetype': 5}
            ]
        })
        result = modelnml.read_output_stream_infos(namelist_data)
        
        assert len(result) == 2
        assert result[0].path == pathlib.Path("./stream1")
        assert result[1].path == pathlib.Path("./stream2")
        assert result[0].stream_index == 0
        assert result[1].stream_index == 1

    def test_custom_filename_format(self):
        """Test that custom filename_format is preserved but path uses it correctly."""
        namelist_data = f90nml.Namelist({
            'output_nml': {
                'output_filename': './output/',
                'filename_format': '<output_filename>custom_<datetime2>',
                'filetype': 5
            }
        })
        result = modelnml.read_output_stream_infos(namelist_data)
        
        assert len(result) == 1
        assert result[0].filename_format == '<output_filename>custom_<datetime2>'
        # Path should be the parent of the resolved format
        assert result[0].path == pathlib.Path("./output")
