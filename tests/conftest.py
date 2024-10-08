import pathlib

import aiida
import aiida.orm
import aiida_testing.mock_code._hasher
import pytest

pytest_plugins = ["aiida.tools.pytest_fixtures", "aiida_testing"]


# TODO: either contribute to aiida_testing or build a simple version here
#   to avoid using protected functionality
class DummyInputHasher(aiida_testing.mock_code._hasher.InputHasher):  # noqa: SLF001 - private member, no other way of doing this
    def __call__(self, cwd: pathlib.Path):  # noqa: ARG002 - unused method argument, superclass compatibility
        return "outputs"


@pytest.fixture
def root_datapath():
    return pathlib.Path(__file__).parent.absolute() / "data"


@pytest.fixture
def simple_icon(mock_code_factory, root_datapath):
    """Mock a code for a simple icon run (no restarts)."""
    datapath = root_datapath / "simple_icon_run"
    return (
        mock_code_factory(
            label="simple-icon",
            entry_point="aiida_icon.icon",
            data_dir_abspath=datapath,
            hasher=DummyInputHasher,
        ),
        datapath,
    )


@pytest.fixture
def restarts_missing(mock_code_factory, root_datapath):
    """Mock an ICON code for a run that should produce restarts but didn't."""
    datapath = root_datapath / "restarts_missing"
    return (
        mock_code_factory(
            label="restarts-missing",
            entry_point="aiida_icon.icon",
            data_dir_abspath=datapath,
            hasher=DummyInputHasher,
        ),
        datapath,
    )


@pytest.fixture
def restarts_present(mock_code_factory, root_datapath):
    """Mock an ICON code for a run that should produce restarts and did."""
    datapath = root_datapath / "restarts_present"
    return (
        mock_code_factory(
            label="restarts-present",
            entry_point="aiida_icon.icon",
            data_dir_abspath=datapath,
            hasher=DummyInputHasher,
        ),
        datapath,
    )


@pytest.fixture
def prepare_builder():
    def preparator(mock_code, datapath):
        builder = mock_code.get_builder()
        builder.master_namelist = aiida.orm.SinglefileData(datapath / "icon_master.namelist")
        builder.model_namelist = aiida.orm.SinglefileData(datapath / "model.namelist")
        builder.dynamics_grid_file = aiida.orm.RemoteData(
            computer=mock_code.computer,
            remote_path=str(datapath.absolute() / "icon_grid_simple.nc"),
        )
        builder.ecrad_data = aiida.orm.RemoteData(
            computer=mock_code.computer,
            remote_path=str(datapath.absolute() / "ecrad_data"),
        )
        builder.rrtmg_sw = aiida.orm.RemoteData(
            computer=mock_code.computer,
            remote_path=str(datapath.absolute() / "rrtmg_sw.nc"),
        )
        builder.cloud_opt_props = aiida.orm.RemoteData(
            computer=mock_code.computer,
            remote_path=str(datapath.absolute() / "ECHAM6_CldOptProps.nc"),
        )
        builder.dmin_wetgrowth_lookup = aiida.orm.RemoteData(
            computer=mock_code.computer,
            remote_path=str(datapath.absolute() / "dmin_wetgrowth_lookup.nc"),
        )
        return builder

    return preparator


@pytest.fixture
def simple_icon_builder(simple_icon, prepare_builder):
    return prepare_builder(*simple_icon)


@pytest.fixture
def restarts_missing_builder(restarts_missing, prepare_builder):
    return prepare_builder(*restarts_missing)


@pytest.fixture
def restarts_present_builder(restarts_present, prepare_builder):
    return prepare_builder(*restarts_present)
