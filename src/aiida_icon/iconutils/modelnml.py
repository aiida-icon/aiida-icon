import pathlib
from typing import NamedTuple

import f90nml

from aiida_icon import exceptions
from aiida_icon.iconutils import namelists


class OutputStreamInfo(NamedTuple):
    """Information about an ICON output stream."""

    path: pathlib.Path
    filename_format: str
    output_filename: str
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


def read_output_stream_info(
    model_nml: namelists.NMLInput,
) -> list[OutputStreamInfo]:
    """Read detailed output stream information from the model namelist."""
    data = namelists.namelists_data(model_nml)
    output_data = data["output_nml"]

    # wrap in list if there is only one
    stream_spec_list: list[f90nml.namelist.Namelist] = (
        [output_data] if isinstance(output_data, f90nml.namelist.Namelist) else output_data
    )

    return [
        OutputStreamInfo(
            path=_out_stream_path(stream_spec),
            output_filename=stream_spec.get("output_filename", ""),
            filename_format=stream_spec.get("filename_format", ""),
            stream_index=i,
        )
        for i, stream_spec in enumerate(stream_spec_list)
    ]


def _out_stream_path(out_stream_spec: f90nml.namelist.Namelist) -> pathlib.Path:
    """Replicate ICON logic in forming the filenames to get the output dir."""

    # output_filename is required, but filename_format is optional
    try:
        output_filename = out_stream_spec["output_filename"]
    except KeyError as e:
        msg = f"Missing required key in output_nml section: {e}"
        raise ValueError(msg) from e

    # filename_format is optional - if missing, assume output_filename is the directory
    filename_format = out_stream_spec.get("filename_format", "")

    # Handle two ICON patterns:
    # 1. output_filename is a directory: './atm_2d/'
    # 2. output_filename is a file prefix: './results/run1'
    if output_filename.endswith("/"):
        # Pattern 1: Directory - use it directly as the output path
        return pathlib.Path(output_filename.rstrip("/"))
    if filename_format:
        # Pattern 2: File prefix with explicit format - construct full filename and take parent directory
        full_path = filename_format.replace("<output_filename>", output_filename)
        return pathlib.Path(full_path).parent
    if "/" in output_filename:
        return pathlib.Path(output_filename).parent
    return pathlib.Path(".")
