import pathlib
import re
import textwrap

import pytest
from aiida import engine, orm
from aiida.common import exceptions as aiidaxc
from aiida.common import folders

from aiida_icon import builder, calculations, tools
from aiida_icon.iconutils import modelnml


@pytest.fixture
def abspath_models_masternml():
    return orm.SinglefileData.from_string(
        textwrap.dedent(
            """
        ! two models, both with an absolute path (assumed to be valid on the hpc machine)
        ! and using the <path> placeholder
        &master_nml
        model_base_dir="/project/experiment/model"
        /
        &master_model_nml
        model_name="foo"
        model_namelist_filename="<path>/foo.nml"
        /
        &master_model_nml
        model_name="bar"
        model_namelist_filename="<path>/bar.nml"
        /
        """
        )
    )


@pytest.fixture
def relpath_models_masternml():
    return orm.SinglefileData.from_string(
        textwrap.dedent(
            """
        ! two models, both with relative path (upload or linking required)
        ! and using the <path> placeholder
        &master_nml
        model_base_dir="model"
        /
        &master_model_nml
        model_name="foo"
        model_namelist_filename="<path>/foo.nml"
        /
        &master_model_nml
        model_name="bar"
        model_namelist_filename="<path>/bar.nml"
        /
        """
        )
    )


@pytest.fixture
def setup_env():
    return orm.SinglefileData.from_string("")


def test_prepare_for_calc(mock_icon_calc, tmp_path):
    prepare_path = tmp_path / "test_prepare_simple"
    prepare_path.mkdir()
    sandbox_folder = folders.SandboxFolder(prepare_path.absolute())
    calcinfo = mock_icon_calc.presubmit(sandbox_folder)

    outputs_2d = sandbox_folder.get_subfolder("simple_icon_run_atm_2d", create=False)
    outputs_3d = sandbox_folder.get_subfolder("simple_icon_run_atm_3d_pl", create=False)
    remote_link_names = [triplet[2] for triplet in calcinfo.remote_symlink_list]
    local_copy_names = [triplet[2] for triplet in calcinfo.local_copy_list]

    assert outputs_2d.exists()
    assert outputs_3d.exists()
    assert "model.namelist" in local_copy_names
    assert "icon_grid_simple.nc" in remote_link_names
    assert "./ecrad_data" in remote_link_names


def test_parser_simple(parser_case, icon_result):
    """Parsed output links and exit code should match expectations."""
    parser = calculations.IconParser(icon_result)
    exit_code = parser.parse()

    assert exit_code.status == parser_case.exit_code

    assert all(link in parser.outputs for link in parser_case.required_output_links)
    assert all(link not in parser.outputs for link in parser_case.disallowed_output_links)
    assert parser.outputs.finish_status.value == parser_case.finish_status_value


@pytest.mark.parametrize("case_name", ["restarts_present"])
def test_additional_restart_parsing(case_name, parser_case, icon_result):
    """Check the contents of restarts related parsing outputs."""
    parser = calculations.IconParser(icon_result)
    parser.parse()
    assert pathlib.Path(parser.outputs.latest_restart_file.get_remote_path()).name == "multifile_restart_atm.mfr"
    assert (
        pathlib.Path(parser.outputs.all_restart_files["restart_20000101T030000Z"].get_remote_path()).name
        == "multifile_restart_atm_20000101T030000Z.mfr"
    )


def test_wrapper_script_autouse(icon_calc_with_wrapper, tmp_path):
    prepare_path = tmp_path / "test_wrapper_script"
    prepare_path.mkdir()
    sandbox_folder = folders.SandboxFolder(prepare_path.absolute())
    calcinfo = icon_calc_with_wrapper.presubmit(sandbox_folder)

    testpath = pathlib.Path(sandbox_folder.get_abs_path("."))

    submit_file = testpath / "_aiidasubmit.sh"
    submit_content = submit_file.read_text()

    assert "wrapper_script" in icon_calc_with_wrapper.inputs
    assert icon_calc_with_wrapper.inputs.metadata.options.mpirun_extra_params == ["./run_icon.sh"]
    assert re.search(r"chmod 755 run_icon.sh", submit_content, re.MULTILINE)
    assert re.search(r"(('mpirun')|('srun')) .* './run_icon.sh'", submit_content, re.MULTILINE)
    assert "run_icon.sh" in [triplet[2] for triplet in calcinfo.local_copy_list]


def test_setup_env_autouse(icon_builder, datapath, add_input_files, tmp_path, setup_env):
    inputs_path = datapath / "simple_icon_run" / "inputs"

    add_input_files(inputs_path, icon_builder)
    icon_builder.setup_env = setup_env

    prepare_path = tmp_path / "test_auto_setupenv"
    prepare_path.mkdir()
    sandbox_folder = folders.SandboxFolder(prepare_path.absolute())
    calcinfo = calculations.IconCalculation(dict(icon_builder)).presubmit(sandbox_folder)

    submit_content = (pathlib.Path(sandbox_folder.get_abs_path(".")) / "_aiidasubmit.sh").read_text()

    assert calcinfo.prepend_text == "source ./setup_env.sh"
    assert re.search(r"source ./setup_env.sh", submit_content, re.MULTILINE)


def test_uenv_autouse(icon_code, datapath, add_input_files, tmp_path):
    prepare_path = tmp_path / "test_autouenv"
    prepare_path.mkdir()
    sandbox_folder = folders.SandboxFolder(prepare_path.absolute())

    tools.code_set_uenv(icon_code, uenv=tools.Uenv(name="foo", view="bar"))
    builder = icon_code.get_builder()
    add_input_files(datapath / "simple_icon_run" / "inputs", builder)
    calc = calculations.IconCalculation(dict(builder))

    _ = calc.presubmit(sandbox_folder)

    submit_content = (pathlib.Path(sandbox_folder.get_abs_path(".")) / "_aiidasubmit.sh").read_text()
    assert re.search(r"#SBATCH --uenv=foo --view=bar", submit_content, re.MULTILINE)


def test_models_namespace_abs_empty(icon_code, datapath, tmp_path, caplog, abspath_models_masternml):
    prepare_path = tmp_path / "test_autouenv"
    prepare_path.mkdir()
    sandbox_folder = folders.SandboxFolder(prepare_path.absolute())

    builder = icon_code.get_builder()
    builder.master_namelist = abspath_models_masternml
    calc = calculations.IconCalculation(dict(builder))
    calcinfo = calc.presubmit(sandbox_folder)

    assert calcinfo.remote_symlink_list == []
    assert calcinfo.remote_copy_list == []
    assert len(calcinfo.local_copy_list) == 1  # only master nml
    assert dict(calc.inputs.models) == {}
    assert re.search(
        r"Warning: Model namelist for model 'foo' is not tracked for provenance",
        caplog.record_tuples[0][2],
        re.MULTILINE,
    )
    assert re.search(
        r"Warning: Model namelist for model 'bar' is not tracked for provenance",
        caplog.record_tuples[1][2],
        re.MULTILINE,
    )


def test_models_namespace_abs_full(icon_code, datapath, tmp_path, caplog, abspath_models_masternml):
    prepare_path = tmp_path / "test_autouenv"
    prepare_path.mkdir()
    sandbox_folder = folders.SandboxFolder(prepare_path.absolute())

    builder = icon_code.get_builder()
    builder.master_namelist = abspath_models_masternml
    builder.models.foo = orm.RemoteData(computer=icon_code.computer, remote_path="/project/experiment/model/foo.nml")
    builder.models.bar = orm.RemoteData(computer=icon_code.computer, remote_path="/some/non/matching/path/bar.nml")
    calc = calculations.IconCalculation(dict(builder))
    calcinfo = calc.presubmit(sandbox_folder)

    assert calcinfo.remote_symlink_list == []
    assert calcinfo.remote_copy_list == []
    assert len(calcinfo.local_copy_list) == 1  # only master nml
    assert re.search(
        r"Remote path .* for model input 'bar' does not match absolute path given in master namelists (.*). Using the path in master namelists.",
        caplog.record_tuples[0][2],
        re.MULTILINE,
    )


def test_models_not_required(icon_code, caplog, abspath_models_masternml):
    ibuilder = builder.IconCalculationBuilder(calculations.IconCalculation)
    ibuilder.code = icon_code
    ibuilder.metadata.dry_run = True
    ibuilder.master_namelist = abspath_models_masternml
    engine.run(ibuilder)
    assert re.search(
        r"Warning: Model namelist for model 'foo' is not tracked for provenance.",
        caplog.record_tuples[0][2],
    )
    assert re.search(
        r"Warning: Model namelist for model 'bar' is not tracked for provenance.",
        caplog.record_tuples[1][2],
    )


def test_models_required(icon_code, relpath_models_masternml):
    ibuilder = builder.IconCalculationBuilder(calculations.IconCalculation)
    ibuilder.code = icon_code
    ibuilder.metadata.dry_run = True
    ibuilder.master_namelist = relpath_models_masternml
    with pytest.raises(aiidaxc.InputValidationError, match=r"Missing input for model 'foo'"):
        engine.run(ibuilder)


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
def test_parser_create_stream_key(icon_parser, output_filename, stream_index, expected_key, test_id):
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
