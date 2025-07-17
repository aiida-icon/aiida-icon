import typing

import aiida
import pytest

from aiida_icon import calculations
from aiida_icon.calculations import IconCalculation
from aiida_icon.iconutils.masternml import modify_master_nml


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

    assert "output_streams" in result, "No output_streams were returned as output."
    output_streams = result["output_streams"]

    # Test structure and keys
    expected_keys = {"simple_icon_run__atm_2d", "simple_icon_run__atm_3d_pl"}
    assert set(output_streams.keys()) == expected_keys, f"Expected keys {expected_keys}, got {set(output_streams.keys())}"

    # Test all values are RemoteData
    assert all(isinstance(stream, aiida.orm.RemoteData) for stream in output_streams.values()), "All output streams should be RemoteData"


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
