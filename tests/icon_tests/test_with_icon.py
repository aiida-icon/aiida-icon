import typing

import aiida
import pytest

from aiida_icon import calculations
from aiida_icon.calculations import IconCalculation
from aiida_icon.iconutils.masternml import modify_master_nml
from tests.utils import assert_output_streams


@pytest.mark.requires_icon
def test_simple_icon_run(simple_icon_run_builder: aiida.engine.ProcessBuilder):
    icon_builder = simple_icon_run_builder

    # First run from scratch
    result, node = aiida.engine.run_get_node(IconCalculation(dict(icon_builder)))

    assert "remote_folder" in result
    remote_path = result["remote_folder"].get_remote_path()

    assert (
        "finish_status" in result
    ), f"Icon run was not successful, no finish_status file found. Please check calculation folder in '{remote_path}'."
    assert (
        result["finish_status"].value == "RESTART"
    ), f"Finish status is not RESTART. Please check calculation folder in '{remote_path}'."

    # Test output streams
    expected_streams_and_files: dict[str, list[str]] = {"simple_icon_run_atm_2d": [], "simple_icon_run_atm_3d_pl": []}

    assert_output_streams(result, node, expected_streams_and_files)

    parser = calculations.IconParser(typing.cast(aiida.orm.CalcJobNode, node))
    exit_code = parser.parse()
    assert (
        exit_code.status == 0
    ), f"Exit code nonzero with message '{exit_code.message}'. Please check calculation folder in '{remote_path}'."
    assert result.get("latest_restart_file", None) is not None, "No 'latest_restart_file' was returned as output."

    # Second run from restart file
    icon_builder.restart_file = result["latest_restart_file"]

    mastern_nml_options = aiida.orm.Dict({"master_nml": {"lrestart": True, "read_restart_namelists": True}})
    icon_builder.master_namelist = modify_master_nml(icon_builder.master_namelist, mastern_nml_options)  # type: ignore[attr-defined]

    result, node = aiida.engine.run_get_node(IconCalculation(dict(icon_builder)))

    assert "remote_folder" in result
    remote_path = result["remote_folder"].get_remote_path()

    assert (
        "finish_status" in result
    ), f"Icon run was not successful, no finish_status file found. Please check calculation folder in '{remote_path}'."
    assert (
        result["finish_status"].value == "OK"
    ), f"Finish status is not OK. Please check calculation folder in '{remote_path}'."
