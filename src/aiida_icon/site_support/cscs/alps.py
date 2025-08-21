import pathlib

from aiida.engine import processes

from aiida_icon import builder, tools

__all__ = ["SCRIPT_DIR", "common_alps_setup"]


SCRIPT_DIR = pathlib.Path(__file__).parent.absolute() / "wrapper_scripts"


def common_alps_setup(icon_builder: processes.ProcessBuilder, *, uenv: tools.Uenv | None = None) -> None:
    """
    Set AiiDA process options for running an aiida_icon.icon calcjob on ALPS.

    Works with both IconCalculationBuilder as well as vanilla ProcessBuilder.

    Examples:

        >>> from aiida_icon import calculations
        >>> vanilla_builder = processes.ProcessBuilder(calculations.IconCalculation)
        >>> vanilla_builder.metadata.options.environment_variables = {"foo": "bar"}
        >>> vanilla_builder.metadata.options.custom_scheduler_commands = (
        ...     "#SBATCH --custom-option=5"
        ... )
        >>> common_alps_setup(vanilla_builder)
        >>> vanilla_builder.metadata.options.environment_variables[
        ...     "CUDA_BUFFER_PAGE_IN_THRESHOLD"
        ... ]
        '0.001'
        >>> vanilla_builder.metadata.options.environment_variables["foo"]
        'bar'
        >>> vanilla_builder.metadata.options.custom_scheduler_commands
        '#SBATCH --custom-option=5\\n#SBATCH --uenv=icon/25.2:v3 --view=default'

        >>> icon_builder = calculations.IconCalculation.get_builder()
        >>> icon_builder.metadata.options.environment_variables = {"foo": "bar"}
        >>> icon_builder.metadata.options.custom_scheduler_commands = (
        ...     "#SBATCH --custom-option=5"
        ... )
        >>> common_alps_setup(icon_builder)
        >>> icon_builder.metadata.options.environment_variables[
        ...     "CUDA_BUFFER_PAGE_IN_THRESHOLD"
        ... ]
        '0.001'
        >>> icon_builder.metadata.options.environment_variables["foo"]
        'bar'
        >>> icon_builder.metadata.options.custom_scheduler_commands
        '#SBATCH --custom-option=5\\n#SBATCH --uenv=icon/25.2:v3 --view=default'
        >>> # With IconCalculationBuilder this is idempotent
        >>> common_alps_setup(icon_builder)
        >>> icon_builder.metadata.options.custom_scheduler_commands
        '#SBATCH --custom-option=5\\n#SBATCH --uenv=icon/25.2:v3 --view=default'

    """
    uenv = uenv or tools.Uenv(name="icon/25.2:v3", view="default")
    options = icon_builder.metadata.options  # type: ignore[attr-defined]  # builder has a custom setattr

    alps_environment_variables = {
        "CUDA_BUFFER_PAGE_IN_THRESHOLD": "0.001",
        "FI_CXI_SAFE_DEVMEM_COPY_THRESHOLD": "0",
        "FI_CXI_RX_MATCH_NODE": "software",
        "FI_MR_CACHE_MONITOR": "disabled",
        "MPICH_GPU_SUPPORT_ENABLED": "1",
        "NVCOMPILER_ACC_DEFER_UPLOADS": "1",
        "NVCOMPILER_TERM": "trace",
        "OMP_NUM_THREADS": "1",
        "ICON_THREADS": "1",
        "OMP_SCHEDULE": "static,1",
        "OMP_DYNAMIC": "false",
        "OMP_STACKSIZE": "200M",
    }
    options.environment_variables = builder.ensure_dict(options.environment_variables) | alps_environment_variables  # type: ignore[attr-defined]
    if isinstance(icon_builder, builder.IconCalculationBuilder):
        icon_builder.set_uenv(uenv.name, view=uenv.view, overwrite=False)
    else:
        options.custom_scheduler_commands = "\n".join(
            [
                *options.custom_scheduler_commands.splitlines(),
                f"#SBATCH --uenv={uenv.name} --view={uenv.view}",
            ]
        )
