import pathlib

import f90nml

from aiida_icon import exceptions
from aiida_icon.iconutils import namelists


def read_restart_file_pattern(model_nml: namelists.NMLInput) -> str:
    data = namelists.namelists_data(model_nml)

    restart_write_mode = data.get("io_nml", {}).get("restart_write_mode", "joint procs multifile")
    if "multifile" not in restart_write_mode:
        raise exceptions.SinglefileRestartNotImplementedError

    return r"multifile_restart_atm_(?P<timestamp>\d{8}T\d{6}Z).mfr"


def read_latest_restart_file_link_name(model_nml: namelists.NMLInput) -> str:
    data = namelists.namelists_data(model_nml)

    restart_write_mode = data.get("io_nml", {}).get("restart_write_mode", "joint procs multifile")
    if "multifile" not in restart_write_mode:
        raise exceptions.SinglefileRestartNotImplementedError

    return "multifile_restart_atm.mfr"


def read_output_stream_paths(
    model_nml: namelists.NMLInput,
) -> list[pathlib.Path]:
    data = namelists.namelists_data(model_nml)

    output_data = data["output_nml"]

    # wrap in list if there is only one
    stream_spec_list: list[f90nml.namelist.Namelist] = (
        [output_data] if isinstance(output_data, f90nml.namelist.Namelist) else output_data
    )

    return [_out_stream_path(stream_spec) for stream_spec in stream_spec_list]


def _out_stream_path(out_stream_spec: f90nml.namelist.Namelist) -> pathlib.Path:
    """Replicate ICON logic in forming the filenames to get the output dir."""

    filename_format = out_stream_spec.get("filename_format", "<output_filename>_XXX_YYY")
    output_filename = out_stream_spec.get("output_filename", "")
    return pathlib.Path(filename_format.replace("<output_filename>", output_filename)).parent
