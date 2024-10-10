import pathlib

import pytest

from aiida_icon import calculations


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
