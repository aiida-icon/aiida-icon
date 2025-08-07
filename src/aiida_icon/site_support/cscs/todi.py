import aiida
from aiida.engine import processes

from aiida_icon import builder, tools
from aiida_icon.site_support.cscs import alps

__all__ = ["setup_for_todi_cpu"]


def setup_for_todi_cpu(icon_builder: processes.ProcessBuilder, *, uenv: tools.Uenv | None = None) -> None:
    """Set up the wrapper script for running on todi."""
    alps.common_alps_setup(icon_builder, uenv=uenv)
    if not isinstance(icon_builder, builder.IconCalculationBuilder):
        builder.prepare_builder_for_wrapper_script(icon_builder)
    icon_builder.wrapper_script = aiida.orm.SinglefileData(file=alps.SCRIPT_DIR / "gh200_cpu.sh")
