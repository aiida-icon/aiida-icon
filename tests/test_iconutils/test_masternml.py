import pathlib
import textwrap

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


@pytest.fixture
def single_model_mn():
    return f90nml.reads(
        textwrap.dedent(
            """
        &master_nml
          model_base_dir="."
        /
        &master_model_nml
          model_name="atm"
          model_namelist_filename="<path>/atm.nml"
        /
        """
        )
    )


@pytest.fixture
def multi_model_mn():
    return f90nml.reads(
        textwrap.dedent(
            """
        &master_nml
          model_base_dir="/absolute/path"
        /
        &master_model_nml
          model_name="foo"
          model_namelist_filename="foo.nml"
        /
        &master_model_nml
          model_name="bar"
          model_namelist_filename="<path>/bar.nml"
        /
        &master_model_nml
          model_name="atm"
          model_namelist_filename="relative/path/atm.nml"
        /
        """
        )
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


def test_iter_model_name_filepath_single(single_model_mn):
    testee = dict(masternml.iter_model_name_filepath(single_model_mn))
    assert str(testee["atm"]) == "atm.nml"
    assert not testee["atm"].is_absolute()


def test_iter_model_name_filepath_multi(multi_model_mn):
    testee = dict(masternml.iter_model_name_filepath(multi_model_mn))
    assert str(testee["foo"]) == "foo.nml"
    assert not testee["foo"].is_absolute()
    assert str(testee["bar"]) == "/absolute/path/bar.nml"
    assert testee["bar"].is_absolute()
    assert str(testee["atm"]) == "relative/path/atm.nml"
    assert not testee["atm"].is_absolute()
