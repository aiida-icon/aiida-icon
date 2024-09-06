import functools
import pathlib

import aiida
import aiida.engine
import aiida.orm

COMPUTER_NAME = "todi"
ICON_CODE_NAME = "icon"

if __name__ == "__main__":
    thisdir = pathlib.Path(__file__).parent.absolute()
    icon = aiida.orm.load_code("icon-runscript@todi")
    make_remote_data = functools.partial(aiida.orm.RemoteData, computer=icon.computer)
    builder = icon.get_builder()
    builder.wrapper_script = aiida.orm.SinglefileData(file=thisdir / "todi_cpu.sh")
    builder.master_namelist = aiida.orm.SinglefileData(file=thisdir / "icon_master.namelist")
    builder.model_namelist = aiida.orm.SinglefileData(file=thisdir / "NAMELIST_exclaim_ape_R02B04")
    builder.dynamics_grid_file = make_remote_data(
        remote_path="/ABSOLUTE_PATH_TO/icon_grid_0013_R02B04_R.nc"
    )  # filename must match the model namelist contents
    builder.ecrad_data = make_remote_data(remote_path="/ABSOLUTE_PATH_TO/ecrad/data")
    builder.rrtmg_sw = make_remote_data(remote_path="/ABSOLUTE_PATH_TO/rrtmg_sw.nc")
    builder.cloud_opt_props = make_remote_data(remote_path="/ABSOLUTE_PATH_TO/ECHAM6_CldOptProps.nc")
    builder.dmin_wetgrowth_lookup = make_remote_data(remote_path="/ABSOLUTE_PATH_TO/dmin_wetgrowth_lookup.nc")
    builder.metadata.options.mpirun_extra_params = [
        "--threads-per-core=1",
        "--distribution=block:block:block",
        "--uenv=icon-wcp/v1:rc4",
        "./run_icon.sh",
    ]
    builder.metadata.description = "Icon on Todi through via wrapper script."
    builder.metadata.options.resources = {"num_machines": 1, "num_mpiprocs_per_machine": 288}
    builder.metadata.options.max_memory_kb = 128000000
    builder.metadata.dry_run = False
    print(aiida.engine.submit(builder))
