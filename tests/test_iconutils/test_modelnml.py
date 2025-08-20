import pathlib
import tempfile
import textwrap

import aiida
import f90nml
import pytest

from aiida_icon.iconutils import modelnml

OUTPUT_STREAM_CASES = [
    ("", 0, []),  # missing output_nml block
    ("&output_nml\n/", 1, [pathlib.Path(".")]),  # empty section
    (  # single stream with explicit path
        """
        &output_nml
          output_filename = './test_output/'
          filename_format = "<output_filename>_<datetime2>"
        /
        """,
        1,
        [pathlib.Path("./test_output")],
    ),
    (  # multiple streams
        """
        &output_nml
         output_filename = './test_output/'
         filename_format = "<output_filename>_<datetime2>"
        /
        """,
        1,
        [pathlib.Path("./test_output")],
    ),
    (  # mixed configurations (some with paths, some without)
        """
        &output_nml
         output_filename = './explicit_path/'
        /
        &output_nml
         filetype = 5
        /
        """,
        2,
        [pathlib.Path("./explicit_path"), pathlib.Path(".")],
    ),
]


@pytest.mark.parametrize(("namelist_content", "expected_count", "expected_paths"), OUTPUT_STREAM_CASES)
def test_read_output_stream_infos(namelist_content, expected_count, expected_paths):
    """Test various namelist configurations and their parsed results."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".nml") as f:
        f.write(textwrap.dedent(namelist_content))
        f.flush()
        model_nml = aiida.orm.SinglefileData(f.name)

    result = modelnml.read_output_stream_infos(model_nml)

    assert len(result) == expected_count
    for i, expected_path in enumerate(expected_paths):
        assert result[i].path == expected_path
        assert result[i].stream_index == i


def test_read_output_stream_infos_default_format(tmp_path):
    """Test that default filename_format is applied when missing."""
    namelist_content = textwrap.dedent(
        """
        &output_nml
         output_filename = './test/'
         filetype = 5
        /
        """
    )
    namelist_file = tmp_path / "default_oustream_format.nml"
    namelist_file.write_text(namelist_content)
    model_nml = aiida.orm.SinglefileData(str(namelist_file))

    result = modelnml.read_output_stream_infos(model_nml)

    assert len(result) == 1
    assert result[0].filename_format == "<output_filename>_XXX_YYY"
    assert result[0].output_filename == "./test/"


def test_read_output_stream_infos_namelist_obj_input():
    """Test parsing when input is already a parsed f90nml namelist object."""
    namelist_data = f90nml.Namelist(
        {
            "output_nml": [
                {
                    "output_filename": "./direct_test/",
                    "filename_format": "<output_filename>_<datetime2>",
                }
            ]
        }
    )

    result = modelnml.read_output_stream_infos(namelist_data)

    assert len(result) == 1
    assert result[0].path == pathlib.Path("./direct_test")


@pytest.mark.parametrize(
    ("output_filename", "stream_index", "expected_key", "test_id"),
    [
        ("./test_output/", 0, "test_output", "simple_path"),
        ("./nested/deep/output/", 1, "nested__deep__output", "nested_path"),
        ("", 5, "stream_05", "fallback_to_index"),
        ("./invalid-chars!@#/", 3, "stream_03", "invalid_chars_fallback"),
        ("./", 0, "stream_00", "root_directory"),
    ],
)
def test_create_stream_key(icon_parser, output_filename, stream_index, expected_key, test_id):
    """Test stream key creation from various output_filename patterns."""
    path = pathlib.Path(output_filename.rstrip("/")) if output_filename else pathlib.Path(".")

    stream_info = modelnml.OutputStreamInfo(
        path=path,
        output_filename=output_filename,
        filename_format="<output_filename>_<datetime2>",
        stream_index=stream_index,
    )

    result = icon_parser._create_stream_key(stream_info)  # noqa: SLF001  # testing private member
    assert result == expected_key
