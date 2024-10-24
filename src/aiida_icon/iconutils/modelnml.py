import aiida.orm
import f90nml

from aiida_icon import exceptions


def read_restart_file_pattern(model_nml: aiida.orm.SinglefileData):
    data = f90nml.reads(model_nml.get_content())

    restart_write_mode = data.get("io_nml", {}).get("restart_write_mode", "joint procs multifile")
    if "multifile" not in restart_write_mode:
        raise exceptions.SinglefileRestartNotImplementedError

    return r"multifile_restart_atm_(?P<timestamp>\d{8}T\d{6}Z).mfr"


def read_latest_restart_file_link_name(model_nml: aiida.orm.SinglefileData):
    data = f90nml.reads(model_nml.get_content())

    restart_write_mode = data.get("io_nml", {}).get("restart_write_mode", "joint procs multifile")
    if "multifile" not in restart_write_mode:
        raise exceptions.SinglefileRestartNotImplementedError

    return "multifile_restart_atm.mfr"
