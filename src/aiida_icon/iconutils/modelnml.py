import aiida.orm
import f90nml


def get_restart_file_pattern(model_nml: aiida.orm.SinglefileData):
    data = f90nml.reads(model_nml.get_content())

    restart_write_mode = data.get("io_nml", {}).get(
        "restart_write_mode", "joint procs multifile"
    )
    if "multifile" not in restart_write_mode:
        raise ValueError("Dealing with non-multifile restart modes is not supported.")

    return r"multifile_atm_\d{8}T\d{6}Z.mfr"


def get_latest_restart_multifile_link(model_nml: aiida.orm.SinglefileData):
    data = f90nml.reads(model_nml.get_content())

    restart_write_mode = data.get("io_nml", {}).get(
        "restart_write_mode", "joint procs multifile"
    )
    if "multifile" not in restart_write_mode:
        raise ValueError("Dealing with non-multifile restart modes is not supported.")

    return "multifile_restart_atm.mfr"
