from __future__ import annotations

import typing
from typing_extensions import Self
import aiida
import aiida.engine

from aiida_icon.calculations import IconCalculation

if typing.TYPE_CHECKING:
    from aiida.engine.processes import ProcessSpec

class Icon(aiida.engine.BaseRestartWorkChain):
    _process_class = IconCalculation

    @classmethod
    def define(cls: type[Self], spec: ProcessSpec) -> None:
        super().define(spec)
        spec.inputs["on_unhandled_failure"].default = "pause"
        spec.expose_inputs(IconCalculation)
        spec.expose_outputs(IconCalculation)
        spec.outline(
            cls.setup,
            aiida.engine.while_(
                cls.should_run_process
            )(
                cls.run_process,
                cls.inspect_process
            ),
            cls.results
        )

    def setup(self: Self) -> None:
        super().setup()
        self.ctx.inputs = self.expose_inputs(IconCalculation)
