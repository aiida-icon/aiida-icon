import dataclasses
import io
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
    return {
        "master_nml": master_options.as_dict(),
        "master_time_control_nml": time_control_options.as_dict(),
    }


@aiida.engine.calcfunction
def modify_master_nml(master_nml: aiida.orm.SinglefileData, options: aiida.orm.Dict) -> aiida.orm.SinglefileData:
    data = f90nml.reads(master_nml.get_content())
    for section in data:
        if section in options:
            data[section] |= options[section]
    string_buffer = io.StringIO()
    f90nml.write(data, string_buffer)
    return aiida.orm.SinglefileData(io.BytesIO(bytes(string_buffer.getvalue(), "utf8")))


def read_lrestart_write_last(master_nml: namelists.NMLInput) -> bool:
    return namelists.namelists_data(master_nml).get("master_nml", {}).get("lrestart_write_last", False)
