import logging
import pathlib
import subprocess
import typing

import aiida
import pytest
import requests

from aiida_icon import calculations
from aiida_icon.calculations import IconCalculation

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
    url = "http://icon-downloads.mpimet.mpg.de/grids/public/edzw/icon_grid_0013_R02B04_R.nc"
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


def test_simple_icon_run(icon_calc: IconCalculation, icon_grid_simple_path: pathlib.Path):
    which_icon = subprocess.run(["which", "icon"], capture_output=True, check=False)
    if which_icon.returncode:
        msg = "Could not find icon executable."
        raise FileNotFoundError(msg)

    filepath_executable = which_icon.stdout.decode().strip()
    # The code from the icon_calc has been already stored and is immutable, so we need to clone it
    code = icon_calc.inputs.code.clone()
    code.filepath_executable = filepath_executable
    code.with_mpi = False
    code.store()
    # aiida allows only assignment by __setattr__ at this point which cannot be
    # detected by the type checker as it is dynamically resolved
    icon_calc.inputs.code = code  # type: ignore[attr-defined]
    icon_calc.inputs.dynamics_grid_file = aiida.orm.RemoteData(  # type: ignore[attr-defined]
        remote_path=str(icon_grid_simple_path), computer=icon_calc.inputs.dynamics_grid_file.computer
    )  # type: ignore[attr-defined]
    result, node = aiida.engine.run_get_node(icon_calc)

    assert "remote_folder" in result
    remote_path = result["remote_folder"].get_remote_path()

    assert (
        "finish_status" in result
    ), f"Icon run was not successful, no finish_status file found. Please check calculation folder in {remote_path}."
    assert (
        result["finish_status"].value == "OK"
    ), "Finish status is not OK. Please check calculation folder in {remote_path}."

    parser = calculations.IconParser(typing.cast(aiida.orm.CalcJobNode, node))
    exit_code = parser.parse()
    assert (
        exit_code.status == 0
    ), f"Exit code nonzero with message '{exit_code.message}'. Please check calculation folder in {remote_path}."
