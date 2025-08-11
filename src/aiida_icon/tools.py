import dataclasses
import pathlib
from typing import NamedTuple

from aiida import orm
from aiida.orm import extras


@dataclasses.dataclass(frozen=True)
class Uenv:
    name: str
    view: str = ""


class OutputStreamInfo(NamedTuple):
    """Information about an ICON output stream."""

    path: pathlib.Path
    output_filename: str
    filename_format: str
    stream_index: int


def code_set_uenv(code: orm.Code, *, uenv: Uenv) -> None:
    code_extras = extras.EntityExtras(code)
    code_extras.set("uenv", dataclasses.asdict(uenv))


def code_get_uenv(code: orm.Code) -> Uenv | None:
    code_extras = extras.EntityExtras(code)
    uenv_extra = code_extras.get("uenv", None)
    if uenv_extra:
        return Uenv(**uenv_extra)
    return None
