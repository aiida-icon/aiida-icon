import pathlib
import tempfile
import textwrap

import aiida.orm
import f90nml

from aiida_icon.iconutils import modelnml


class TestReadOutputStreamInfos:
    """Test the parsing of output stream information from model namelists."""

    def test_missing_output_nml_section(self):
        """Test handling when output_nml section is completely missing."""
        # Create a namelist without output_nml section
        namelist_content = textwrap.dedent("""
            &grid_nml
             dynamics_grid_filename = "icon_grid_simple.nc"
            /

            &radiation_nml
             ecrad_data_path = './ecrad_data'
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            _ = f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        # Should return empty list when no output_nml section exists
        assert result == []

    def test_empty_output_nml_section(self):
        """Test handling when output_nml section exists but is empty."""
        namelist_content = textwrap.dedent("""
            &grid_nml
             dynamics_grid_filename = "icon_grid_simple.nc"
            /

            &output_nml
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        # Should handle empty output_nml section gracefully
        assert len(result) == 1
        assert result[0].output_filename == ""
        assert result[0].filename_format == "<output_filename>_XXX_YYY"
        assert result[0].path == pathlib.Path(".")
        assert result[0].stream_index == 0

    def test_missing_output_filename(self):
        """Test handling when output_filename is not specified in output_nml."""
        namelist_content = textwrap.dedent("""
            &output_nml
             filetype = 5
             output_interval = "PT1H"
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 1
        assert result[0].output_filename == ""
        assert result[0].filename_format == "<output_filename>_XXX_YYY"
        assert result[0].path == pathlib.Path(".")
        assert result[0].stream_index == 0

    def test_aquaplanet_style_output_filename(self):
        """Test aquaplanet case where output_filename is a subdirectory ending with '/'."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './aquaplanet_output/'
             filename_format = "<output_filename>_<datetime2>"
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 1
        assert result[0].output_filename == "./aquaplanet_output/"
        assert result[0].filename_format == "<output_filename>_<datetime2>"
        assert result[0].path == pathlib.Path("./aquaplanet_output")
        assert result[0].stream_index == 0

    def test_explicit_output_filename(self):
        """Test normal case with explicit output_filename."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './exclaim_ape_R02B04_atm_2d/'
             filename_format = "<output_filename>_<datetime2>"
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 1
        assert result[0].output_filename == "./exclaim_ape_R02B04_atm_2d/"
        assert result[0].filename_format == "<output_filename>_<datetime2>"
        assert result[0].path == pathlib.Path("./exclaim_ape_R02B04_atm_2d")
        assert result[0].stream_index == 0

    def test_multiple_output_streams(self):
        """Test parsing multiple output streams."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './stream1_output/'
             filename_format = "<output_filename>_<datetime2>"
             filetype = 5
            /

            &output_nml
             output_filename = './stream2_output/'
             filename_format = "<output_filename>_<datetime2>"
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 2

        # First stream
        assert result[0].output_filename == "./stream1_output/"
        assert result[0].path == pathlib.Path("./stream1_output")
        assert result[0].stream_index == 0

        # Second stream
        assert result[1].output_filename == "./stream2_output/"
        assert result[1].path == pathlib.Path("./stream2_output")
        assert result[1].stream_index == 1

    def test_custom_filename_format(self):
        """Test parsing with custom filename_format."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './custom_output/'
             filename_format = "<output_filename>_custom_<datetime2>"
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 1
        assert result[0].output_filename == "./custom_output/"
        assert result[0].filename_format == "<output_filename>_custom_<datetime2>"
        # TODO: Check if this path should be what is given in output_filename
        assert result[0].path == pathlib.Path("custom_output")
        assert result[0].stream_index == 0

    def test_missing_filename_format(self):
        """Test handling when filename_format is not specified."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './test_output/'
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 1
        assert result[0].output_filename == "./test_output/"
        assert result[0].filename_format == "<output_filename>_XXX_YYY"  # Default value
        assert result[0].path == pathlib.Path("./test_output")
        assert result[0].stream_index == 0

    def test_complex_path_structures(self):
        """Test parsing with complex nested path structures."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './nested/deep/output/'
             filename_format = "<output_filename>_result_<datetime2>"
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 1
        assert result[0].output_filename == "./nested/deep/output/"
        assert result[0].path == pathlib.Path("./nested/deep/output")
        assert result[0].stream_index == 0

    def test_mixed_output_streams(self):
        """Test parsing streams with different configurations."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './stream_with_path/'
             filename_format = "<output_filename>_<datetime2>"
             filetype = 5
            /

            &output_nml
             filetype = 5
            /

            &output_nml
             output_filename = './another_stream/'
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 3

        # First stream: explicit path and format
        assert result[0].output_filename == "./stream_with_path/"
        assert result[0].path == pathlib.Path("./stream_with_path")
        assert result[0].stream_index == 0

        # Second stream: missing both path and format
        assert result[1].output_filename == ""
        assert result[1].path == pathlib.Path(".")
        assert result[1].stream_index == 1

        # Third stream: path but default format
        assert result[2].output_filename == "./another_stream/"
        assert result[2].path == pathlib.Path("./another_stream")
        assert result[2].stream_index == 2

    def test_with_f90nml_namelist_object(self):
        """Test parsing when input is already a parsed f90nml namelist object."""
        namelist_data = f90nml.Namelist(
            {
                "output_nml": [
                    {
                        "output_filename": "./direct_nml_test/",
                        "filename_format": "<output_filename>_<datetime2>",
                        "filetype": 5,
                    }
                ]
            }
        )

        result = modelnml.read_output_stream_infos(namelist_data)

        assert len(result) == 1
        assert result[0].output_filename == "./direct_nml_test/"
        assert result[0].path == pathlib.Path("./direct_nml_test")
        assert result[0].stream_index == 0

    def test_edge_case_root_directory_output(self):
        """Test edge case where output goes to root directory."""
        namelist_content = textwrap.dedent("""
            &output_nml
             output_filename = './'
             filename_format = "<output_filename>results_<datetime2>"
             filetype = 5
            /
        """)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nml", delete=False) as f:
            f.write(namelist_content)
            f.flush()

            model_nml = aiida.orm.SinglefileData(f.name)

        result = modelnml.read_output_stream_infos(model_nml)

        assert len(result) == 1
        assert result[0].output_filename == "./"
        assert result[0].path == pathlib.Path(".")
        assert result[0].stream_index == 0
