import pathlib

import aiida
import aiida.engine


def test_parser_simple(simple_icon_builder):
    """Parsing should pass in the simplest possible case"""
    results, node = aiida.engine.run_get_node(simple_icon_builder)

    assert node.is_finished_ok
    assert node.outputs.finish_status.value == "OK"
    assert node.exit_code is None


def test_parser_missing_restarts(restarts_missing_builder):
    """
    Parsing should fail but not except when restart multifiles are expected and not found.

    Everything but the restart files should still be parsed normally.
    """
    results, node = aiida.engine.run_get_node(restarts_missing_builder)

    assert not node.is_finished_ok
    assert node.outputs.finish_status.value == "RESTART"
    assert "lastest_restart_file" not in node.outputs
    assert "all_restart_files" not in node.outputs
    assert node.exit_code.status == 304


def test_parser_present_restarts(restarts_present_builder):
    """Parsing should pass when restart multifiles are expected and found."""
    results, node = aiida.engine.run_get_node(restarts_present_builder)

    assert node.is_finished_ok
    assert node.outputs.finish_status.value == "RESTART"
    assert pathlib.Path(node.outputs.latest_restart_file.get_remote_path()).name == "multifile_restart_atm.mfr"
    assert (
        pathlib.Path(node.outputs.all_restart_files["restart_20000101T030000Z"].get_remote_path()).name
        == "multifile_restart_atm_20000101T030000Z.mfr"
    )
    assert node.exit_code is None
