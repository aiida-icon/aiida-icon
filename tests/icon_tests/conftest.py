import functools
import logging
import pathlib
import subprocess
import typing

import aiida
import pytest
import requests

LOGGER = logging.getLogger(__name__)


class DownloadError(RuntimeError):
    def __init__(self, url: str, response: requests.Response):
        super().__init__(f"Failed downloading file {url} , exited with response {response}")


def download_file(url: str, file_path: pathlib.Path):
    response = requests.get(url)
    if not response.ok:
        raise DownloadError(url, response)

    file_path.write_bytes(response.content)


@pytest.fixture(scope="module")
def icon_grid_simple_path(pytestconfig):
    url = "https://github.com/agoscinski/icon-testfiles/raw/refs/heads/main/icon_grid_0013_R02B04_R.nc"
    filename = "icon_grid_simple.nc"
    cache_dir = pytestconfig.cache.mkdir("downloaded_files")
    icon_grid_path = cache_dir / filename

    # Check if the file is already cached
    if icon_grid_path.exists():
        LOGGER.info("Found icon grid in cache, reusing it.")
    else:
        # File is not cached, download and save it
        LOGGER.info("Downloading and caching icon grid.")
        download_file(url, icon_grid_path)

    return icon_grid_path


@pytest.fixture
def icon_filepath_executable() -> str:
    which_icon = subprocess.run(["which", "icon"], capture_output=True, check=False)
    if which_icon.returncode:
        msg = "Could not find icon executable."
        raise FileNotFoundError(msg)

    return which_icon.stdout.decode().strip()


@pytest.fixture
def simple_icon_run_builder(
    aiida_code_installed: typing.Callable[..., aiida.orm.InstalledCode],
    aiida_computer_local: typing.Callable[[], aiida.orm.Computer],
    icon_filepath_executable: str,
    datapath: pathlib.Path,
    icon_grid_simple_path: pathlib.Path,
) -> aiida.engine.ProcessBuilder:
    localhost_computer = aiida_computer_local()
    code = aiida_code_installed(
        default_calc_job_plugin="icon.icon",
        computer=localhost_computer,
        filepath_executable=icon_filepath_executable,
        with_mpi=False,
    )

    inputs_path = datapath.absolute() / "simple_icon_run" / "inputs"
    builder = code.get_builder()
    make_remote = functools.partial(aiida.orm.RemoteData, computer=code.computer)
    builder.master_namelist = aiida.orm.SinglefileData(inputs_path / "icon_master.namelist")
    builder.models.atm = aiida.orm.SinglefileData(inputs_path / "model.namelist")  # type: ignore[attr-defined] # dynamic port namespace
    builder.dynamics_grid_file = aiida.orm.RemoteData(
        remote_path=str(icon_grid_simple_path), computer=localhost_computer
    )
    builder.ecrad_data = make_remote(remote_path=str(inputs_path / "ecrad_data"))
    builder.rrtmg_sw = make_remote(remote_path=str(inputs_path / "rrtmg_sw.nc"))
    builder.cloud_opt_props = make_remote(remote_path=str(inputs_path / "ECHAM6_CldOptProps.nc"))
    builder.dmin_wetgrowth_lookup = make_remote(remote_path=str(inputs_path / "dmin_wetgrowth_lookup.nc"))
    return builder
