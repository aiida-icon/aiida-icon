from __future__ import annotations

import typing

import aiida
import aiida.engine

from aiida_icon.calculations import IconCalculation

if typing.TYPE_CHECKING:
    from aiida.engine.processes.workchains.workchain import WorkChainSpec
    from typing_extensions import Self


class Icon(aiida.engine.BaseRestartWorkChain):
    _process_class = IconCalculation

    @classmethod
    def define(cls: type[Self], spec: WorkChainSpec) -> None:  # type: ignore[override] # aiida-core and plumpy disagree
        super().define(spec)
        spec.inputs["on_unhandled_failure"].default = "pause"  # type: ignore[union-attr] # .default might be added by metaprog
        spec.expose_inputs(IconCalculation)
        spec.expose_outputs(IconCalculation)
        spec.outline(
            cls.setup,  # type: ignore[arg-type] # inadequate type hints in aiida-core
            aiida.engine.while_(cls.should_run_process)(  # type: ignore[arg-type] # inadequate type hints in aiida-core
                cls.run_process,  # type: ignore[arg-type] # inadequate type hints in aiida-core
                cls.inspect_process,  # type: ignore[arg-type] # inadequate type hints in aiida-core
            ),  # type: ignore[arg-type] # inadequate type hints in aiida-core
            cls.results,  # type: ignore[arg-type] # inadequate type hints in aiida-core
        )

    def setup(self: Self) -> None:
        super().setup()
        self.ctx.inputs = self.exposed_inputs(IconCalculation)
