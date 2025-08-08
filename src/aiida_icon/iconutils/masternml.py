from __future__ import annotations

import dataclasses
import io
import pathlib
import typing
from typing import Any

import aiida.engine
import aiida.orm
import f90nml

from aiida_icon.iconutils import namelists


@dataclasses.dataclass
class OptionsMixin:
    """
    Overrides mixin for dataclasses.

    Add an as_dict method, which ignores keys with value None.
    """

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}


@dataclasses.dataclass
class MasterOptions(OptionsMixin):
    lrestart: bool | None = None
    read_restart_namelists: bool | None = None


@dataclasses.dataclass
class TimeControlOptions(OptionsMixin):
    experiment_start_date: str | None = None
    experiment_stop_date: str | None = None
    restart_time_int_val: str | None = None
    checkpoint_time_int_val: str | None = None


def options(master_options: MasterOptions, time_control_options: TimeControlOptions) -> dict[str, dict[str, Any]]:
    """
    Modifiable master namelist options.

    Examples:
        >>> options(
        ...     master_options=MasterOptions(lrestart=True),
        ...     time_control_options=TimeControlOptions(),
        ... )
        {'master_nml': {'lrestart': True}, 'master_time_control_nml': {}}
    """
    return {
        "master_nml": master_options.as_dict(),
        "master_time_control_nml": time_control_options.as_dict(),
    }


@aiida.engine.calcfunction
def modify_master_nml(master_nml: aiida.orm.SinglefileData, options: aiida.orm.Dict) -> aiida.orm.SinglefileData:
    """
    Provenance preserving master_namelist modifications.

    Examples:
        >>> pytest_plugins = ["aiida.tools.pytest_fixtures"]
        >>> old_master = aiida.orm.SinglefileData.from_string(
        ...     content=(
        ...         "&master_nml\\nlrestart=.false.\\nread_restart_namelists=.true.\\n/"
        ...         "\\n&master_time_control_nml\\ncalendar='proleptic gregorian'\\n/"
        ...     )
        ... )
        >>> new_master = modify_master_nml(
        ...     master_nml=old_master,
        ...     options=options(
        ...         master_options=MasterOptions(lrestart=True),
        ...         time_control_options=TimeControlOptions(),
        ...     ),
        ... )
        >>> new_data = f90nml.reads(new_master.get_content(mode="r"))
        >>> new_data["master_nml"]
        Namelist({'lrestart': True, 'read_restart_namelists': True})
        >>> new_data["master_time_control_nml"]
        Namelist({'calendar': 'proleptic gregorian'})
    """
    data = f90nml.reads(master_nml.get_content(mode="r"))
    for section in data:
        if section in options:
            data[section] |= options[section]
    string_buffer = io.StringIO()
    f90nml.write(data, string_buffer)
    return aiida.orm.SinglefileData(io.BytesIO(bytes(string_buffer.getvalue(), "utf8")))


def read_lrestart_write_last(master_nml: namelists.NMLInput) -> bool:
    return namelists.namelists_data(master_nml).get("master_nml", {}).get("lrestart_write_last", False)


def iter_model_namelists(master_nml: namelists.NMLInput) -> typing.Iterator[f90nml.namelist.Namelist]:
    """
    Iterate over all model namelists blocks in a master namelist

    Examples:
        >>> list(
        ...     iter_model_namelists(
        ...         f90nml.reads(
        ...             "&master_model_nml\\nmodel_name='atm'\\n/\\n&master_model_nml\\nmodel_name='foo'\\n/"
        ...         )
        ...     )
        ... )
        [Namelist({'model_name': 'atm'}), Namelist({'model_name': 'foo'})]
    """
    data = namelists.namelists_data(master_nml)

    models = data.get("master_model_nml", [])
    if isinstance(models, f90nml.namelist.Namelist):
        models = [models]

    yield from models


def iter_model_namelists_filepaths(master_nml: f90nml.namelist.Namelist) -> typing.Iterator[tuple[str, pathlib.Path]]:
    data = namelists.namelists_data(master_nml)
    base_path = data.get("model_base_dir", "")
    for model in iter_model_namelists(master_nml):
        filename = model["model_namelist_filename"].replace("<path>", r"{path}").format(path=base_path)
        yield model["model_name"], pathlib.Path(filename)
