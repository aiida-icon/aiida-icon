from __future__ import annotations

import typing

from aiida import orm
from aiida.engine.processes import builder as process_builder

from aiida_icon import tools

if typing.TYPE_CHECKING:
    from collections.abc import Callable

ItemT = typing.TypeVar("ItemT")


def ensure_list(current_value: list[ItemT] | Callable[[], list[ItemT]]) -> list[ItemT]:
    """
    Turn a list factory into a list but leave lists untouched.

    Example:
        >>> factory = lambda: ["foo", "bar"]
        >>> ensure_list(factory)
        ['foo', 'bar']
        >>> ensure_list(["foobar"])
        ['foobar']
        >>> ensure_list(list)
        []
    """

    match current_value:
        case list():
            return current_value
        case _ if callable(current_value):
            return current_value()
        case _:
            raise TypeError


def ensure_dict(
    current_value: dict[str, ItemT] | Callable[[], dict[str, ItemT]],
) -> dict[str, ItemT]:
    """
    Turn a dict factory into a dict but leave dicts untouched.

    Example:
        >>> factory = lambda: {"foo": "bar"}
        >>> ensure_dict(factory)
        {'foo': 'bar'}
        >>> ensure_dict({"bar": "foo"})
        {'bar': 'foo'}
        >>> ensure_dict(dict)
        {}
    """

    match current_value:
        case dict():
            return current_value
        case _ if callable(current_value):
            return current_value()
        case _:
            raise TypeError


def prepare_builder_for_wrapper_script(
    builder: process_builder.ProcessBuilder, *, filename: str = "run_icon.sh"
) -> None:
    builder.metadata.options.prepend_text = "\n".join(  # type: ignore[attr-defined]
        [
            *builder.metadata.options.prepend_text.splitlines(),  # type: ignore[attr-defined]
            f"chmod 755 {filename}",
        ]
    )
    current_mpirun_extra_params = ensure_list(
        builder.metadata.options.mpirun_extra_params  # type: ignore[attr-defined]
    )
    builder.metadata.options.mpirun_extra_params = [  # type: ignore[attr-defined]
        *current_mpirun_extra_params,
        f"./{filename}",
    ]


class IconCalculationBuilder(process_builder.ProcessBuilder):
    """
    Custom ProcessBuilder for IconCalculation.

    This ensures that setting `.wrapper_script` on the builder takes care of
    setting the options required to use the wrapper script.

    This slightly changes the semantics of the `mpirun_extra_params` option
    in the presence of a wrapper script input. Check the examples section below
    for details.

    Additionally, if the code is set to a code, which has a "uenv" set
    (via aiida_icon.tools.code_set_uenv), configure the UENV to be used automatically.

    Examples:

        >>> pytest_plugins = ["aiida.tools.pytest_fixtures"]
        >>> from aiida import orm
        >>> from aiida_icon.calculations import IconCalculation
        >>> builder = IconCalculationBuilder(IconCalculation)
        >>> builder.wrapper_script = orm.SinglefileData(__file__)
        >>> builder.metadata.options.prepend_text
        'chmod 755 run_icon.sh'
        >>> builder.metadata.options.mpirun_extra_params
        ['./run_icon.sh']

        in order for additional mpirun params to not be considered params of the run script,
        we need to prepend them from now on

        >>> # add an additional mpirun option
        >>> builder.metadata.options.mpirun_extra_params.insert(-1, "--mpirun-option")
        >>> # add an option to the wrapper script
        >>> builder.metadata.options.mpirun_extra_params.append("--wrapper-script-option")

        >>> from aiida_icon import tools
        >>> code = getfixture("aiida_code_installed")()
        >>> tools.code_set_uenv(code, uenv=tools.Uenv("foo", "bar"))
        >>> builder = IconCalculationBuilder(IconCalculation)
        >>> builder.code = code
        >>> builder.metadata.options.custom_scheduler_commands
        '#SBATCH --uenv=foo --view=bar'
    """

    def __setattr__(self, attr: str, value: typing.Any) -> None:
        if attr == "wrapper_script":
            prepare_builder_for_wrapper_script(self)
        if attr == "code" and isinstance(value, orm.Code) and (uenv := tools.code_get_uenv(value)):
            self.set_uenv(uenv.name, view=uenv.view)
        super().__setattr__(attr, value)

    def set_uenv(self, uenv_name: str, *, view: str = "", overwrite: bool = False) -> None:
        """
        Conveniently configure to run using a UENV (useful for CSCS ALPS machines).

        Assumes the target machine is using SLURM and has the uenv plugin installed.

        Example:

            >>> from aiida_icon.calculations import IconCalculation
            >>> builder = IconCalculationBuilder(IconCalculation)
            >>> builder.set_uenv("icon/25.2:v3", view="default")
            >>> builder.metadata.options.custom_scheduler_commands
            '#SBATCH --uenv=icon/25.2:v3 --view=default'
        """
        if getattr(self, "__is_uenv_set", False) and not overwrite:
            return
        current_custom_scheduler_commands: str = (
            self.metadata.options.custom_scheduler_commands  # type: ignore[attr-defined]
        )
        lines = current_custom_scheduler_commands.splitlines()
        uenv_line = f"#SBATCH --uenv={uenv_name}"
        if view:
            uenv_line = f"{uenv_line} --view={view}"
        lines.append(uenv_line)
        self.metadata.options.custom_scheduler_commands = "\n".join(lines)  # type: ignore[attr-defined]
        setattr(self, "__is_uenv_set", True)
