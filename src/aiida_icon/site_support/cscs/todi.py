import pathlib
import textwrap

import aiida
from aiida.engine import processes

SCRIPT_DIR = pathlib.Path(__file__).parent.absolute() / "wrapper_scripts"


# TODO(ricoh): allow custom images
def common_alps_setup(builder: processes.ProcessBuilder) -> None:
    """
    Set AiiDA process options for running an aiida_icon.icon calcjob on ALPS.

    Needs to be used with the `wrapper_script` input of the IconCalculation.
    """
    options = builder.metadata.options  # type: ignore[attr-defined]  # builder has a custom setattr
    options.custom_scheduler_commands = "\n".join(
        [
            *options.custom_scheduler_commands.splitlines(),
            "#SBATCH --uenv=icon-wcp/v1:rc4",
        ]
    )
    options.environment_variables = {
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
    options.prepend_text = textwrap.dedent(
        """
        chmod 755 run_icon.sh
        """
    )
    options.mpirun_extra_params.append("./run_icon.sh")


def setup_for_todi_cpu(builder: processes.ProcessBuilder) -> None:
    common_alps_setup(builder)
    builder.wrapper_script = aiida.orm.SinglefileData(file=SCRIPT_DIR / "todi_cpu.sh")
