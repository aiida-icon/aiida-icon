import pathlib
from typing import NamedTuple

import f90nml

from aiida_icon import exceptions
from aiida_icon.iconutils import namelists


class OutputStreamInfo(NamedTuple):
    """Information about an ICON output stream."""

    path: pathlib.Path
    output_filename: str
    filename_format: str
    stream_index: int


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


def read_output_stream_infos(
    model_nml: namelists.NMLInput,
) -> list[OutputStreamInfo]:
    """Read detailed output stream information from the model namelist."""
    data = namelists.namelists_data(model_nml)
    output_data = data.get("output_nml", f90nml.namelist.Namelist())
    output_data = data.get("output_nml", [])

    # wrap in list if there is only one
    stream_spec_list: list[f90nml.namelist.Namelist] = (
        [output_data] if isinstance(output_data, f90nml.namelist.Namelist) else output_data
    )

    output_streams = []
    for i, stream_spec in enumerate(stream_spec_list):
        # Replicate ICON logic in forming the filenames to get the output dir
        filename_format = stream_spec.get("filename_format", "<output_filename>_XXX_YYY")
        output_filename = stream_spec.get("output_filename", "")
        path = pathlib.Path(filename_format.replace("<output_filename>", output_filename)).parent

        output_streams.append(
            OutputStreamInfo(
                path=path,
                output_filename=output_filename,
                filename_format=filename_format,
                stream_index=i,
            )
        )

    return output_streams
