import pathlib

import aiida
import aiida.orm
import f90nml
import pytest

from aiida_icon.iconutils import masternml


@pytest.fixture
def empty_options():
    return masternml.options(
        master_options=masternml.MasterOptions(),
        time_control_options=masternml.TimeControlOptions(),
    )


@pytest.fixture
def write_restart_options():
    return masternml.options(
        master_options=masternml.MasterOptions(lrestart=True),
        time_control_options=masternml.TimeControlOptions(
            experiment_start_date="2000-01-01T00:00:00Z",
            experiment_stop_date="2000-01-01T06:00:00Z",
            restart_time_int_val="PT3H",
            checkpoint_time_int_val="PT3H",
        ),
    )


def test_options_empty(empty_options):
    assert empty_options == {"master_nml": {}, "master_time_control_nml": {}}


def test_write_restart_options(write_restart_options):
    assert write_restart_options == {
        "master_nml": {"lrestart": True},
        "master_time_control_nml": {
            "experiment_start_date": "2000-01-01T00:00:00Z",
            "experiment_stop_date": "2000-01-01T06:00:00Z",
            "restart_time_int_val": "PT3H",
            "checkpoint_time_int_val": "PT3H",
        },
    }


def test_modify_master_nml(write_restart_options):
    master_nml = aiida.orm.SinglefileData(
        pathlib.Path(__file__).parent.parent.parent / "examples" / "exclaim_R02B04" / "icon_master.namelist"
    )
    options = aiida.orm.Dict(write_restart_options)
    modified = masternml.modify_master_nml(master_nml, options)

    assert master_nml.is_stored
    assert options.is_stored
    assert modified.is_stored

    data = f90nml.reads(modified.get_content())
    for section, section_data in options.items():
        for key, value in section_data.items():
            assert data[section][key] == value
