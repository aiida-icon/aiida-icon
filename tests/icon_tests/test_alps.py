import pathlib
from typing import Any

import aiida
import aiida.engine
import aiida.orm
import pytest

from aiida_icon import tools
from aiida_icon.site_support import cscs
from tests.utils import assert_output_streams


@pytest.fixture(scope="session", autouse=True)
def aiida_config() -> None:
    return None


@pytest.fixture(scope="session", autouse=True)
def aiida_profile() -> None:
    aiida.load_profile("cscsci")


@pytest.fixture
def santis() -> aiida.orm.Computer:
    return aiida.orm.load_computer("santis")


@pytest.fixture
def icon_base_path() -> pathlib.Path:
    return pathlib.Path("/capstor/store/cscs/userlab/cwd01/leclairm/archive_icon_build/icon-nwp_cpu_25.2-v3")


@pytest.fixture
def icon(santis, icon_base_path) -> aiida.orm.InstalledCode:
    code = aiida.orm.InstalledCode(
        computer=santis,
        filepath_executable=str(icon_base_path / "bin" / "icon"),
        default_calc_job_plugin="icon.icon",
    )
    code.store()
    tools.code_set_uenv(code, uenv=tools.Uenv(name="icon/25.2:v3", view="default"))
    return code


@pytest.fixture
def experiment_path() -> pathlib.Path:
    return pathlib.Path("/capstor/store/cscs/userlab/cwd01/leclairm/Sirocco_test_cases/exclaim_ape_R02B04")


@pytest.fixture
def experiment_remotedata(experiment_path, santis) -> aiida.orm.RemoteData:
    return aiida.orm.RemoteData(remote_path=str(experiment_path), computer=santis)


@pytest.fixture
def master_nml(datapath) -> aiida.orm.SinglefileData:
    filename = "icon_master.namelist"
    filepath = str(datapath / "r2b4_inputs" / filename)
    return aiida.orm.SinglefileData(file=filepath)


@pytest.fixture
def atm_nml(datapath) -> aiida.orm.SinglefileData:
    filename = "NAMELIST_exclaim_ape_R02B04"
    filepath = str(datapath / "r2b4_inputs" / filename)
    return aiida.orm.SinglefileData(file=filepath)


@pytest.fixture
def grid_file(experiment_path, santis) -> aiida.orm.RemoteData:
    return aiida.orm.RemoteData(remote_path=str(experiment_path / "icon_grid_0013_R02B04_R.nc"), computer=santis)


@pytest.fixture
def initdata_remotes(icon_base_path, santis) -> dict[str, aiida.orm.RemoteData]:
    initdata_path = icon_base_path / "data"
    return {
        "ecrad_data": aiida.orm.RemoteData(
            remote_path=str(icon_base_path / "externals" / "ecrad" / "data"),
            computer=santis,
        ),
        "rrtmg_sw": aiida.orm.RemoteData(remote_path=str(initdata_path / "rrtmg_sw.nc"), computer=santis),
        "cloud_opt_props": aiida.orm.RemoteData(
            remote_path=str(initdata_path / "ECHAM6_CldOptProps.nc"), computer=santis
        ),
        "dmin_wetgrowth_lookup": aiida.orm.RemoteData(
            remote_path=str(initdata_path / "dmin_wetgrowth_graupelhail_cosmo5.nc"),
            computer=santis,
        ),
    }


@pytest.fixture
def metadata() -> dict[str, Any]:
    return {
        "options": {
            "mpirun_extra_params": [
                "--threads-per-core=1",
                "--distribution=block:block:block",
            ],
            "resources": {
                "num_machines": 1,
                "num_mpiprocs_per_machine": 288,
            },
            "max_wallclock_seconds": 5 * 60,
            "max_memory_kb": 128 * 1000000,
            "queue_name": "debug",
            "account": "csstaff",
        }
    }


@pytest.mark.cscsci
def test_r2b4_santis(icon, master_nml, atm_nml, grid_file, initdata_remotes, metadata):
    builder = icon.get_builder()
    builder.master_namelist = master_nml
    builder.models.atm = atm_nml
    builder.dynamics_grid_file = grid_file
    for key, value in initdata_remotes.items():
        builder[key] = value
    builder._merge({"metadata": metadata})  # noqa: SLF001 # _merge is not private, merely named to avoid clashes
    cscs.santis.setup_for_santis_cpu(builder)
    res, node = aiida.engine.run_get_node(builder)
    print(f"workdir: {node.get_remote_workdir()}")  # noqa: T201 # leave this to be able to check the workdir in case of failure

    assert node.process_state is aiida.engine.ProcessState.FINISHED
    assert "remote_folder" in res
    assert "retrieved" in res
    assert "finish_status" in res
    assert node.exit_status == 0
    assert node.exit_message is None
    assert node.exit_code is None

    # Test output streams with expected files
    expected_streams_and_files = {
        "exclaim_ape_R02B04_atm_2d": ["_20000101T000003Z.nc"],
        "exclaim_ape_R02B04_atm_3d_pl": ["_20000101T000000Z.nc"],
    }

    assert_output_streams(res, node, expected_streams_and_files)
